CREATE TABLE IF NOT EXISTS pt48_ajuste_importacoes (
    id SERIAL PRIMARY KEY,
    periodo_inicio DATE NOT NULL,
    periodo_fim DATE NOT NULL,
    arquivo_ajustes VARCHAR(255) NOT NULL,
    criado_por_usuario_id INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_pt48_ajuste_importacoes_periodo_inicio
    ON pt48_ajuste_importacoes(periodo_inicio);
CREATE INDEX IF NOT EXISTS ix_pt48_ajuste_importacoes_periodo_fim
    ON pt48_ajuste_importacoes(periodo_fim);

CREATE TABLE IF NOT EXISTS pt48_ajustes (
    id SERIAL PRIMARY KEY,
    importacao_id INTEGER NOT NULL REFERENCES pt48_ajuste_importacoes(id) ON DELETE CASCADE,
    colaborador_id INTEGER REFERENCES colaboradores(id) ON DELETE SET NULL,
    nome_colaborador VARCHAR(255) NOT NULL,
    nome_normalizado VARCHAR(255) NOT NULL,
    match_status VARCHAR(20) NOT NULL DEFAULT 'unmatched',
    data DATE NOT NULL,
    entrada_1 VARCHAR(5),
    saida_1 VARCHAR(5),
    entrada_2 VARCHAR(5),
    saida_2 VARCHAR(5),
    entrada_3 VARCHAR(5),
    saida_3 VARCHAR(5),
    quantidade_batidas INTEGER NOT NULL DEFAULT 0,
    batida_impar BOOLEAN NOT NULL DEFAULT FALSE,
    ajustado_por VARCHAR(255),
    alterado_em TIMESTAMP,
    solicitado_em TIMESTAMP,
    motivo VARCHAR(255),
    solicitacao BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_pt48_ajustes_importacao_id ON pt48_ajustes(importacao_id);
CREATE INDEX IF NOT EXISTS ix_pt48_ajustes_colaborador_id ON pt48_ajustes(colaborador_id);
CREATE INDEX IF NOT EXISTS ix_pt48_ajustes_nome_normalizado ON pt48_ajustes(nome_normalizado);
CREATE INDEX IF NOT EXISTS ix_pt48_ajustes_data ON pt48_ajustes(data);
