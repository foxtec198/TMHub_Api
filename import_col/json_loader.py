from import_col.cols import _cidade_para


def prepare_uploaded_json(data):
    if not isinstance(data, dict) or not isinstance(data.get("centros_de_custo"), list):
        raise ValueError("informe a lista 'centros_de_custo'")

    employees = []
    for group in data["centros_de_custo"]:
        if not isinstance(group, dict):
            continue
        center_name = group.get("centro_de_custo")
        center_id = center_name.split(" - ", 1)[0].strip() if center_name else None
        department, city_id, city_name = _cidade_para(center_id)
        group_employees = group.get("empregados") or []
        if not isinstance(group_employees, list):
            raise ValueError(f"a lista de empregados de '{center_name}' é inválida")
        for source in group_employees:
            if not isinstance(source, dict):
                continue
            employee = dict(source)
            employee["centro_custo"] = center_name
            employee["centro_custo_num"] = center_id
            employee["departamento_codigo"] = department
            employee["cidade_id"] = city_id
            employee["cidade"] = city_name
            employees.append(employee)
    return employees
