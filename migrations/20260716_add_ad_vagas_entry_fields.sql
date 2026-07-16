ALTER TABLE ad_vagas
    ADD COLUMN IF NOT EXISTS colaborador_entrada VARCHAR,
    ADD COLUMN IF NOT EXISTS data_aviso DATE;

COMMENT ON COLUMN ad_vagas.colaborador_entrada IS
    'Nome informado manualmente para a pessoa que ocupará a vaga, antes do cadastro em colaboradores';

COMMENT ON COLUMN ad_vagas.data_aviso IS
    'Data em que o supervisor avisou a vaga ou encaminhou o currículo ao responsável';
