from flask import request as rq, jsonify, send_file
from models.usuarios import Users, db
from utils.check_field import check_field
from hashlib import sha256
from utils.safe_route import safe_route
from datetime import datetime as dt, timedelta
from email.message import EmailMessage
from os import getenv
import re
import secrets
import smtplib
from io import BytesIO
from openpyxl import Workbook, load_workbook
from models.filiais import Branch, filial_usuarios
from utils.filial_scope import is_admin
from utils.permissions import PERMISSION_CATALOG, replace_permissions, serialize_permissions
from utils.password_security import (
    hash_password,
    is_default_password,
    is_strong_password,
    verify_password,
)
from utils.token import create_token
from utils.user_requirements import (
    auth_requirements,
    is_valid_cpf,
    normalize_cpf,
    refresh_user_requirements,
    validate_profile_photo,
)

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

class UserServices:
    @staticmethod
    def _is_admin(token_data):
        return is_admin(token_data)

    @staticmethod
    def _normalize_cpf(value):
        return normalize_cpf(value)

    @staticmethod
    def _issue_token(user):
        persistent = bool(user.token_sem_expiracao)
        return create_token({
            "id": user.id,
            "perm": user.role,
            "ver": int(user.token_version or 0),
            "sessao_persistente": persistent,
        }, expires=not persistent)

    @safe_route
    def read(self, token_data):
        detailed = rq.args.get("detail") == "1"
        include_photo = rq.args.get("include_photo") == "1"
        admin = self._is_admin(token_data)
        if detailed and not admin:
            return jsonify("Apenas administradores podem consultar configurações de usuários."), 403

        users_query = Users.query
        if not admin:
            current_user_branches = filial_usuarios.alias("current_user_branches")
            branch_ids = db.session.query(current_user_branches.c.filial_id).filter(
                current_user_branches.c.usuario_id == token_data.get("id")
            )
            users_query = (
                users_query.join(
                    filial_usuarios,
                    filial_usuarios.c.usuario_id == Users.id,
                )
                .filter(filial_usuarios.c.filial_id.in_(branch_ids))
                .distinct()
            )
        users = users_query.order_by(Users.nome).all()

        if not detailed:
            return jsonify([{
                "id": user.id,
                "nome": user.nome,
                **({"foto_perfil": user.foto_perfil} if include_photo else {}),
            } for user in users]), 200

        return jsonify([{
            "id": user.id,
            "nome": user.nome,
            "email": user.email,
            "cpf": user.cpf if admin else None,
            "role": user.role,
            "gerencia_faltas": bool(user.gerencia_faltas),
            "created_at": user.created_at,
            "last_login": user.last_login,
            "filial_ids": sorted(branch.id for branch in user.filiais),
            "permissions": serialize_permissions(user),
            **({"foto_perfil": user.foto_perfil} if include_photo else {}),
        } for user in users]), 200

    @safe_route
    def create(self, token_data):
        if not self._is_admin(token_data):
            return jsonify("Apenas administradores podem criar usuários."), 403

        user, error = self._build_user(rq.get_json(silent=True) or {})
        if error:
            return jsonify(error), 400

        branch_error = self._apply_branches(user, rq.get_json(silent=True) or {})
        if branch_error:
            return jsonify(branch_error), 400
        db.session.add(user)
        db.session.flush()
        permission_error = replace_permissions(user, (rq.get_json(silent=True) or {}).get("permissions"))
        if permission_error:
            db.session.rollback()
            return jsonify(permission_error), 400
        db.session.commit()
        return jsonify(self._serialize_admin(user)), 201

    @safe_route
    def update(self, token_data):
        if not self._is_admin(token_data):
            return jsonify("Apenas administradores podem modificar usuários."), 403

        body = rq.get_json(silent=True) or {}
        user = db.session.get(Users, body.get("id"))
        if not user:
            return jsonify("Usuário não encontrado."), 404

        error = self._apply_user_changes(user, body)
        if error:
            return jsonify(error), 400

        branch_error = self._apply_branches(user, body)
        if branch_error:
            return jsonify(branch_error), 400
        permission_error = replace_permissions(user, body.get("permissions") if "permissions" in body else None)
        if permission_error:
            db.session.rollback()
            return jsonify(permission_error), 400

        db.session.commit()
        return jsonify(self._serialize_admin(user)), 200

    @safe_route
    def delete(self): ...

    @safe_route
    def import_users(self, token_data):
        if not self._is_admin(token_data):
            return jsonify("Apenas administradores podem importar usuários."), 403

        uploaded = rq.files.get("file")
        if not uploaded or not uploaded.filename.lower().endswith(".xlsx"):
            return jsonify("Envie uma planilha no formato .xlsx."), 400

        try:
            workbook = load_workbook(uploaded.stream, read_only=True, data_only=True)
            rows = workbook.active.iter_rows(values_only=True)
            headers = [str(value or "").strip().lower() for value in next(rows)]
        except (StopIteration, ValueError, OSError):
            return jsonify("Não foi possível ler a planilha."), 400

        required = ["nome", "cpf", "email", "role", "password"]
        if any(header not in headers for header in required):
            return jsonify(f"A planilha deve conter as colunas: {', '.join(required)}."), 400

        indexes = {header: headers.index(header) for header in required}
        created = []
        errors = []

        for row_number, row in enumerate(rows, start=2):
            if not any(value is not None and str(value).strip() for value in row):
                continue
            if row_number > 1001:
                errors.append("A planilha pode conter no máximo 1000 usuários.")
                break

            data = {key: row[indexes[key]] for key in required}
            user, error = self._build_user(data)
            if error:
                errors.append(f"Linha {row_number}: {error}")
                continue
            db.session.add(user)
            db.session.flush()
            created.append(user)

        if errors:
            db.session.rollback()
            return jsonify({"message": "A importação foi cancelada.", "errors": errors}), 400
        if not created:
            return jsonify("A planilha não contém usuários para importar."), 400

        db.session.commit()
        return jsonify({"message": f"{len(created)} usuários importados com sucesso.", "total": len(created)}), 201

    @safe_route
    def download_template(self, token_data):
        if not self._is_admin(token_data):
            return jsonify("Apenas administradores podem baixar o modelo de importação."), 403

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Usuarios"
        worksheet.append(["nome", "cpf", "email", "role", "password"])
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = "A1:E1"
        for column, width in {"A": 32, "B": 16, "C": 34, "D": 12, "E": 24}.items():
            worksheet.column_dimensions[column].width = width

        instructions = workbook.create_sheet("Instrucoes")
        instructions.append(["Campo", "Regra"])
        instructions.append(["nome", "Obrigatório"])
        instructions.append(["cpf", "Opcional; quando informado, use 11 dígitos sem pontuação"])
        instructions.append(["email", "Opcional, válido e único"])
        instructions.append(["role", "SUPERVISOR, GERENTE, USER ou ADMIN"])
        instructions.append(["password", "Mínimo 8 caracteres, com maiúscula, minúscula, número e símbolo"])

        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name="modelo_importacao_usuarios.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def _build_user(self, body):
        nome = str(body.get("nome") or "").strip()
        cpf = self._normalize_cpf(body.get("cpf")) or None
        email = str(body.get("email") or "").strip().lower() or None
        role = str(body.get("role") or "USER").strip().upper()
        password = str(body.get("password") or "")

        ok, error = check_field(nome=nome, senha=password)
        if not ok:
            return None, error
        if cpf and not is_valid_cpf(cpf):
            return None, "Informe um CPF válido."
        if email and not EMAIL_PATTERN.fullmatch(email):
            return None, "Informe um e-mail válido."
        if role not in {"SUPERVISOR", "GERENTE", "USER", "ADMIN"}:
            return None, "A role deve ser SUPERVISOR, GERENTE, USER ou ADMIN."
        if not is_strong_password(password):
            return None, "A senha deve ter ao menos 8 caracteres, com maiúscula, minúscula, número e caractere especial."
        if cpf and Users.query.filter_by(cpf=cpf).first():
            return None, "CPF já cadastrado."
        if email and Users.query.filter_by(email=email).first():
            return None, "E-mail já cadastrado."

        return Users(
            nome=nome,
            cpf=cpf,
            email=email,
            role=role,
            gerencia_faltas=bool(body.get("gerencia_faltas", False)),
            hash=hash_password(password),
            primeiro_acesso=True,
            cpf_pendente=not bool(cpf),
            foto_pendente=False,
            troca_senha_obrigatoria=False,
            senha_padrao=is_default_password(password),
            token_version=0,
        ), None

    def _apply_user_changes(self, user, body):
        if not any(key in body for key in ("nome", "cpf", "email", "role", "password", "filial_ids", "gerencia_faltas", "permissions")):
            return "Nenhuma alteração informada."

        if "nome" in body:
            nome = str(body.get("nome") or "").strip()
            if len(nome) < 2:
                return "Informe um nome válido."
            user.nome = nome

        if "cpf" in body:
            cpf = self._normalize_cpf(body.get("cpf")) or None
            if cpf and not is_valid_cpf(cpf):
                return "Informe um CPF válido."
            if cpf and Users.query.filter(Users.cpf == cpf, Users.id != user.id).first():
                return "CPF já cadastrado."
            user.cpf = cpf

        if "email" in body:
            email = str(body.get("email") or "").strip().lower() or None
            if email and not EMAIL_PATTERN.fullmatch(email):
                return "Informe um e-mail válido."
            if email and Users.query.filter(Users.email == email, Users.id != user.id).first():
                return "E-mail já cadastrado."
            user.email = email

        if "role" in body:
            role = str(body.get("role") or "").strip().upper()
            if role not in {"SUPERVISOR", "GERENTE", "USER", "ADMIN"}:
                return "A role deve ser SUPERVISOR, GERENTE, USER ou ADMIN."
            user.role = role

        if body.get("password"):
            password = str(body["password"])
            if not is_strong_password(password):
                return "A senha deve ter ao menos 8 caracteres, com maiúscula, minúscula, número e caractere especial."
            user.hash = hash_password(password)
            user.senha_padrao = is_default_password(password)
            user.troca_senha_obrigatoria = False
            user.token_version = int(user.token_version or 0) + 1
            user.senha_alterada_em = dt.now()

        if "gerencia_faltas" in body:
            user.gerencia_faltas = bool(body.get("gerencia_faltas"))

        refresh_user_requirements(user)
        return None

    @staticmethod
    def _apply_branches(user, body):
        if "filial_ids" not in body:
            return None
        try:
            ids = {int(value) for value in (body.get("filial_ids") or [])}
        except (TypeError, ValueError):
            return "Informe filiais válidas."
        branches = Branch.query.filter(Branch.id.in_(ids), Branch.ativa.is_(True)).all() if ids else []
        if len(branches) != len(ids):
            return "Uma ou mais filiais não foram encontradas ou estão inativas."
        user.filiais = branches
        return None

    @staticmethod
    def _serialize_admin(user):
        return {
            "id": user.id,
            "nome": user.nome,
            "email": user.email,
            "cpf": user.cpf,
            "role": user.role,
            "gerencia_faltas": bool(user.gerencia_faltas),
            "created_at": user.created_at,
            "last_login": user.last_login,
            "filial_ids": sorted(branch.id for branch in user.filiais),
            "permissions": serialize_permissions(user),
        }

    @safe_route
    def profile(self, token_data):
        user = db.session.get(Users, token_data.get("id"))
        if not user:
            return jsonify("Usuário não encontrado."), 404
        return jsonify(self._serialize(user))

    @safe_route
    def support_admins(self, token_data):
        admins = (
            Users.query
            .filter(db.func.upper(Users.role) == "ADMIN")
            .order_by(Users.nome)
            .all()
        )
        return jsonify([
            {
                "id": admin.id,
                "nome": admin.nome,
                "foto_perfil": admin.foto_perfil,
            }
            for admin in admins
        ]), 200

    @safe_route
    def update_profile(self, token_data):
        user = db.session.get(Users, token_data.get("id"))
        if not user:
            return jsonify("Usuário não encontrado."), 404

        body = rq.get_json(silent=True) or {}
        nome = body.get("nome")
        foto = body.get("foto_perfil")
        tema = body.get("tema")
        modo_tema = body.get("modo_tema")
        senha_atual = body.get("senha_atual")
        nova_senha = body.get("nova_senha")
        has_timo_update = "timo_ativo" in body
        timo_ativo = body.get("timo_ativo")

        if nome is not None:
            nome = nome.strip()
            if len(nome) < 2 or len(nome) > 120:
                return jsonify("O nome deve ter entre 2 e 120 caracteres."), 400
            user.nome = nome

        if foto is not None:
            if foto and not validate_profile_photo(foto):
                return jsonify("A foto deve ser PNG, JPG ou WEBP e ter até 1,5 MB."), 400
            user.foto_perfil = foto or None

        if tema is not None:
            tema = str(tema).lower()
            if tema not in {"tmhub", "light", "dark", "cyberpunk", "pride", "christmas"}:
                return jsonify("Tema visual inválido."), 400
            if tema in {"light", "dark"}:
                if modo_tema is None:
                    user.modo_tema = tema
                user.tema = "tmhub"
            else:
                user.tema = tema

        if modo_tema is not None:
            modo_tema = str(modo_tema).lower()
            if modo_tema not in {"light", "dark"}:
                return jsonify("O modo deve ser light ou dark."), 400
            user.modo_tema = modo_tema

        if has_timo_update:
            if str(user.role or "").upper() != "ADMIN":
                return jsonify("A ativação do Timo está disponível apenas para administradores."), 403
            if not isinstance(timo_ativo, bool):
                return jsonify("Informe um valor válido para ativar ou desativar o Timo."), 400
            user.timo_ativo = timo_ativo

        if nova_senha is not None:
            valid_password, _, _ = verify_password(str(senha_atual or ""), user.hash)
            if not valid_password:
                return jsonify("Senha atual incorreta."), 400
            if not is_strong_password(nova_senha):
                return jsonify("A senha deve ter ao menos 8 caracteres, com maiúscula, minúscula, número e caractere especial."), 400
            user.hash = hash_password(nova_senha)
            user.senha_padrao = is_default_password(nova_senha)
            user.troca_senha_obrigatoria = False
            user.token_version = int(user.token_version or 0) + 1
            user.senha_alterada_em = dt.now()

        if not any(value is not None for value in (nome, foto, tema, modo_tema, nova_senha)) and not has_timo_update:
            return jsonify("Nenhuma alteração informada."), 400

        refresh_user_requirements(user)
        db.session.commit()
        if tema is not None or modo_tema is not None:
            # O mascote desktop não depende do browser, então recebe a paleta
            # logo após o usuário trocar o tema na própria conta.
            from models.timo_voice_agents import TimoUserPreference
            from utils.timo_voice_socket import emit_agent_control

            preference = db.session.get(TimoUserPreference, user.id)
            if preference and preference.agente_preferido_id:
                emit_agent_control(
                    preference.agente_preferido_id,
                    bool(preference.habilitado),
                )
        response = self._serialize(user)
        if nova_senha is not None:
            response["access_token"] = self._issue_token(user)
        return jsonify(response)

    @safe_route
    def request_email_code(self, token_data):
        user = db.session.get(Users, token_data.get("id"))
        body = rq.get_json(silent=True) or {}
        email = str(body.get("email", "")).strip().lower()
        if not user:
            return jsonify("Usuário não encontrado."), 404
        if not EMAIL_PATTERN.fullmatch(email):
            return jsonify("Informe um e-mail válido."), 400
        if Users.query.filter(Users.email == email, Users.id != user.id).first():
            return jsonify("Este e-mail já está em uso."), 409

        code = f"{secrets.randbelow(1_000_000):06d}"
        try:
            self._send_email_code(email, code)
        except (OSError, RuntimeError, smtplib.SMTPException):
            return jsonify("O serviço de e-mail não está disponível no momento."), 503
        user.email_pendente = email
        user.email_codigo_hash = sha256(code.encode()).hexdigest()
        user.email_codigo_expira_em = dt.now() + timedelta(minutes=10)
        db.session.commit()
        return jsonify("Código enviado. Ele expira em 10 minutos."), 200

    @safe_route
    def confirm_email(self, token_data):
        user = db.session.get(Users, token_data.get("id"))
        code = str((rq.get_json(silent=True) or {}).get("codigo", "")).strip()
        if not user:
            return jsonify("Usuário não encontrado."), 404
        if not user.email_pendente or not user.email_codigo_hash:
            return jsonify("Solicite um novo código de verificação."), 400
        if not user.email_codigo_expira_em or user.email_codigo_expira_em < dt.now():
            return jsonify("O código expirou. Solicite um novo."), 400
        if sha256(code.encode()).hexdigest() != user.email_codigo_hash:
            return jsonify("Código de verificação inválido."), 400

        user.email = user.email_pendente
        user.email_pendente = None
        user.email_codigo_hash = None
        user.email_codigo_expira_em = None
        db.session.commit()
        return jsonify(self._serialize(user))

    @safe_route
    def pending_requirements(self, token_data):
        user = db.session.get(Users, token_data.get("id"))
        if not user:
            return jsonify("Usuário não encontrado."), 404
        return jsonify({
            "requirements": auth_requirements(user),
            "cpf": user.cpf,
            "foto_perfil": user.foto_perfil,
        })

    @safe_route
    def complete_required_profile(self, token_data):
        user = db.session.get(Users, token_data.get("id"))
        if not user:
            return jsonify("Usuário não encontrado."), 404
        body = rq.get_json(silent=True) or {}
        cpf = normalize_cpf(body.get("cpf") if "cpf" in body else user.cpf)
        photo = body.get("foto_perfil") if "foto_perfil" in body else None
        if not is_valid_cpf(cpf):
            return jsonify("Informe um CPF válido."), 400
        if Users.query.filter(Users.cpf == cpf, Users.id != user.id).first():
            return jsonify("CPF já cadastrado para outro usuário."), 409
        if photo and not validate_profile_photo(photo):
            return jsonify("A foto deve ser PNG, JPG ou WEBP e ter até 1,5 MB."), 400

        user.cpf = cpf
        if photo:
            user.foto_perfil = photo
        refresh_user_requirements(user)
        db.session.commit()
        return jsonify({
            "requirements": auth_requirements(user),
            "cpf": user.cpf,
            "foto_perfil": user.foto_perfil,
        })

    @safe_route
    def change_required_password(self, token_data):
        user = db.session.get(Users, token_data.get("id"))
        if not user:
            return jsonify("Usuário não encontrado."), 404
        requirements = auth_requirements(user)
        if requirements["cpf_pendente"]:
            return jsonify("Conclua o cadastro do CPF primeiro."), 409

        new_password = str((rq.get_json(silent=True) or {}).get("nova_senha") or "")
        if not is_strong_password(new_password):
            return jsonify("A senha deve ter ao menos 8 caracteres, com maiúscula, minúscula, número e caractere especial."), 400
        if is_default_password(new_password):
            return jsonify("Escolha uma senha diferente da senha padrão."), 400
        same_password, _, _ = verify_password(new_password, user.hash)
        if same_password:
            return jsonify("A nova senha deve ser diferente da senha atual."), 400

        user.hash = hash_password(new_password)
        user.troca_senha_obrigatoria = False
        user.senha_padrao = False
        user.token_version = int(user.token_version or 0) + 1
        user.senha_alterada_em = dt.now()
        db.session.commit()
        token = self._issue_token(user)
        return jsonify({
            "access_token": token,
            "requirements": auth_requirements(user),
        })

    @safe_route
    def ignore_default_password(self, token_data):
        user = db.session.get(Users, token_data.get("id"))
        if not user:
            return jsonify("Usuário não encontrado."), 404
        requirements = auth_requirements(user)
        if requirements["cpf_pendente"]:
            return jsonify("Conclua o cadastro do CPF primeiro."), 409
        if not user.senha_padrao:
            return jsonify({"requirements": requirements})
        user.senha_padrao = False
        db.session.commit()
        return jsonify({"requirements": auth_requirements(user)})

    @staticmethod
    def _serialize(user):
        return {
            "id": user.id,
            "nome": user.nome,
            "email": user.email,
            "foto_perfil": user.foto_perfil,
            "tema": user.tema or "tmhub",
            "modo_tema": user.modo_tema or "light",
            "role": user.role,
            "timo_ativo": bool(user.timo_ativo) if str(user.role or "").upper() == "ADMIN" else False,
            "gerencia_faltas": bool(user.gerencia_faltas),
            "filiais": [{"id": branch.id, "nome": branch.nome} for branch in sorted(user.filiais, key=lambda item: item.nome) if branch.ativa],
            "permissions": serialize_permissions(user),
            "requirements": auth_requirements(user),
        }

    @safe_route
    def permission_catalog(self, token_data):
        if not self._is_admin(token_data):
            return jsonify("Apenas administradores podem consultar o catálogo de permissões."), 403
        return jsonify(PERMISSION_CATALOG), 200

    @staticmethod
    def _send_email_code(recipient, code):
        host = getenv("SMTP_HOST")
        sender = getenv("SMTP_FROM") or getenv("SMTP_USER")
        if not host or not sender:
            raise RuntimeError("SMTP_HOST e SMTP_FROM (ou SMTP_USER) devem estar configurados.")

        message = EmailMessage()
        message["Subject"] = "Confirme a troca de e-mail - TM Hub"
        message["From"] = sender
        message["To"] = recipient
        message.set_content(f"Seu código de verificação é {code}. Ele expira em 10 minutos.")

        port = int(getenv("SMTP_PORT", "587"))
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            if getenv("SMTP_STARTTLS", "true").lower() == "true":
                smtp.starttls()
            username = getenv("SMTP_USER") or sender
            password = getenv("SMTP_PASSWORD")
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)
