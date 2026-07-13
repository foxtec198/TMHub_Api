CREATE TABLE IF NOT EXISTS pt48_importacoes (
    id SERIAL PRIMARY KEY,
    periodo_inicio DATE NOT NULL,
    periodo_fim DATE NOT NULL,
    arquivo_absenteismo VARCHAR(255) NOT NULL,
    arquivo_horas_extras VARCHAR(255) NOT NULL,
    criado_por_usuario_id INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_pt48_importacoes_periodo_inicio ON pt48_importacoes(periodo_inicio);
CREATE INDEX IF NOT EXISTS ix_pt48_importacoes_periodo_fim ON pt48_importacoes(periodo_fim);

CREATE TABLE IF NOT EXISTS pt48_absenteismo (
    id SERIAL PRIMARY KEY,
    importacao_id INTEGER NOT NULL REFERENCES pt48_importacoes(id) ON DELETE CASCADE,
    colaborador_id INTEGER REFERENCES colaboradores(id) ON DELETE SET NULL,
    nome_colaborador VARCHAR(255) NOT NULL,
    nome_normalizado VARCHAR(255) NOT NULL,
    match_status VARCHAR(20) NOT NULL DEFAULT 'unmatched',
    previsto_minutos INTEGER NOT NULL DEFAULT 0,
    ausencia_minutos INTEGER NOT NULL DEFAULT 0,
    presenca_minutos INTEGER NOT NULL DEFAULT 0,
    abs_percentual NUMERIC(7, 2) NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS ix_pt48_absenteismo_importacao_id ON pt48_absenteismo(importacao_id);
CREATE INDEX IF NOT EXISTS ix_pt48_absenteismo_colaborador_id ON pt48_absenteismo(colaborador_id);
CREATE INDEX IF NOT EXISTS ix_pt48_absenteismo_nome_normalizado ON pt48_absenteismo(nome_normalizado);

CREATE TABLE IF NOT EXISTS pt48_horas_extras (
    id SERIAL PRIMARY KEY,
    importacao_id INTEGER NOT NULL REFERENCES pt48_importacoes(id) ON DELETE CASCADE,
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
    horas_normais_minutos INTEGER NOT NULL DEFAULT 0,
    horas_extras_minutos INTEGER NOT NULL DEFAULT 0,
    motivo VARCHAR(255),
    quantidade_batidas INTEGER NOT NULL DEFAULT 0,
    batida_impar BOOLEAN NOT NULL DEFAULT FALSE,
    batida_irregular BOOLEAN NOT NULL DEFAULT FALSE,
    irregularidade VARCHAR(500)
);

CREATE INDEX IF NOT EXISTS ix_pt48_horas_extras_importacao_id ON pt48_horas_extras(importacao_id);
CREATE INDEX IF NOT EXISTS ix_pt48_horas_extras_colaborador_id ON pt48_horas_extras(colaborador_id);
CREATE INDEX IF NOT EXISTS ix_pt48_horas_extras_nome_normalizado ON pt48_horas_extras(nome_normalizado);
CREATE INDEX IF NOT EXISTS ix_pt48_horas_extras_data ON pt48_horas_extras(data);
