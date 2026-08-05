BEGIN;

ALTER TABLE colaboradores
    ADD COLUMN IF NOT EXISTS cpf VARCHAR(20),
    ADD COLUMN IF NOT EXISTS tm_ops_password_hash VARCHAR(255),
    ADD COLUMN IF NOT EXISTS tm_ops_ativo BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS tm_ops_primeiro_acesso BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS tm_ops_ultimo_acesso TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS tm_ops_perfil VARCHAR(30) NOT NULL DEFAULT 'executor',
    ADD COLUMN IF NOT EXISTS tm_ops_token_version INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS tm_ops_migration_audit (
    id BIGSERIAL PRIMARY KEY,
    tipo VARCHAR(40) NOT NULL,
    acesso_id INTEGER,
    colaborador_id INTEGER,
    detalhes JSONB NOT NULL DEFAULT '{}'::jsonb,
    registrado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $migration$
BEGIN
    IF to_regclass('public.schedular_acessos') IS NOT NULL THEN
        INSERT INTO tm_ops_migration_audit (tipo, acesso_id, colaborador_id, detalhes)
        SELECT
            'COLABORADOR_NAO_ENCONTRADO',
            acesso.id,
            acesso.colaborador_id,
            jsonb_build_object('perfil', acesso.perfil, 'ativo', acesso.ativo)
        FROM schedular_acessos acesso
        LEFT JOIN colaboradores colaborador ON colaborador.id = acesso.colaborador_id
        WHERE colaborador.id IS NULL;

        INSERT INTO tm_ops_migration_audit (tipo, colaborador_id, detalhes)
        SELECT
            'ACESSO_DUPLICADO',
            acesso.colaborador_id,
            jsonb_build_object(
                'quantidade', COUNT(*),
                'acesso_ids', jsonb_agg(acesso.id ORDER BY acesso.updated_at DESC NULLS LAST, acesso.id DESC)
            )
        FROM schedular_acessos acesso
        GROUP BY acesso.colaborador_id
        HAVING COUNT(*) > 1;

        UPDATE colaboradores colaborador
        SET
            tm_ops_password_hash = origem.senha_hash,
            tm_ops_ativo = origem.ativo,
            tm_ops_primeiro_acesso = origem.senha_pendente,
            tm_ops_ultimo_acesso = origem.ultimo_login,
            tm_ops_perfil = COALESCE(origem.perfil, 'executor'),
            tm_ops_token_version = COALESCE(origem.token_version, 0)
        FROM (
            SELECT DISTINCT ON (acesso.colaborador_id)
                acesso.colaborador_id,
                acesso.senha_hash,
                acesso.ativo,
                acesso.senha_pendente,
                acesso.ultimo_login,
                acesso.perfil,
                acesso.token_version
            FROM schedular_acessos acesso
            JOIN colaboradores colaborador ON colaborador.id = acesso.colaborador_id
            ORDER BY acesso.colaborador_id, acesso.updated_at DESC NULLS LAST, acesso.id DESC
        ) origem
        WHERE colaborador.id = origem.colaborador_id;

        IF to_regclass('public.schedular_acessos_legacy') IS NULL THEN
            ALTER TABLE schedular_acessos RENAME TO schedular_acessos_legacy;
        END IF;
    END IF;
END
$migration$;

-- Compatibilidade temporária para instâncias antigas da API que ainda
-- consultam schedular_acessos durante a janela entre migration e deploy.
CREATE OR REPLACE FUNCTION sync_schedular_legacy_to_tm_ops()
RETURNS TRIGGER AS $sync$
BEGIN
    IF TG_OP = 'DELETE' THEN
        UPDATE colaboradores
        SET
            tm_ops_ativo = FALSE,
            tm_ops_token_version = COALESCE(tm_ops_token_version, 0) + 1
        WHERE id = OLD.colaborador_id;
        RETURN OLD;
    END IF;

    UPDATE colaboradores
    SET
        tm_ops_password_hash = NEW.senha_hash,
        tm_ops_ativo = NEW.ativo,
        tm_ops_primeiro_acesso = NEW.senha_pendente,
        tm_ops_ultimo_acesso = NEW.ultimo_login,
        tm_ops_perfil = COALESCE(NEW.perfil, 'executor'),
        tm_ops_token_version = COALESCE(NEW.token_version, 0)
    WHERE id = NEW.colaborador_id;
    RETURN NEW;
END
$sync$ LANGUAGE plpgsql;

DO $compatibility$
BEGIN
    IF to_regclass('public.schedular_acessos_legacy') IS NOT NULL THEN
        DROP TRIGGER IF EXISTS trg_schedular_legacy_tm_ops
            ON schedular_acessos_legacy;
        CREATE TRIGGER trg_schedular_legacy_tm_ops
            AFTER INSERT OR UPDATE OR DELETE ON schedular_acessos_legacy
            FOR EACH ROW EXECUTE FUNCTION sync_schedular_legacy_to_tm_ops();

        IF to_regclass('public.schedular_acessos') IS NULL THEN
            EXECUTE 'CREATE VIEW schedular_acessos AS SELECT * FROM schedular_acessos_legacy';
        END IF;
    END IF;
END
$compatibility$;

DELETE FROM usuario_permissoes antiga
USING usuario_permissoes atual
WHERE antiga.usuario_id = atual.usuario_id
  AND antiga.tela = 'schedular'
  AND atual.tela = 'tm_ops';

UPDATE usuario_permissoes
SET tela = 'tm_ops', updated_at = NOW()
WHERE tela = 'schedular';

CREATE INDEX IF NOT EXISTS ix_colaboradores_tm_ops_ativo
    ON colaboradores (tm_ops_ativo)
    WHERE tm_ops_ativo = TRUE;
CREATE INDEX IF NOT EXISTS ix_colaboradores_nome_busca
    ON colaboradores (LOWER(nome) text_pattern_ops);
CREATE INDEX IF NOT EXISTS ix_colaboradores_centro_id
    ON colaboradores (centro_id);
CREATE INDEX IF NOT EXISTS ix_colaboradores_cpf_busca
    ON colaboradores (cpf text_pattern_ops);

COMMIT;

-- Conferência obrigatória apó a execução:
-- SELECT * FROM tm_ops_migration_audit ORDER BY registrado_em, id;
-- SELECT COUNT(*) FROM colaboradores WHERE tm_ops_password_hash IS NOT NULL;
