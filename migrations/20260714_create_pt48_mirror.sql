CREATE TABLE IF NOT EXISTS pt48_espelho_importacoes (
    id SERIAL PRIMARY KEY,
    periodo_inicio DATE NOT NULL,
    periodo_fim DATE NOT NULL,
    arquivo_espelho VARCHAR(255) NOT NULL,
    criado_por_usuario_id INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_pt48_espelho_importacoes_periodo_inicio
    ON pt48_espelho_importacoes(periodo_inicio);
CREATE INDEX IF NOT EXISTS ix_pt48_espelho_importacoes_periodo_fim
    ON pt48_espelho_importacoes(periodo_fim);

CREATE TABLE IF NOT EXISTS pt48_espelho_ponto (
    id SERIAL PRIMARY KEY,
    importacao_id INTEGER NOT NULL REFERENCES pt48_espelho_importacoes(id) ON DELETE CASCADE,
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
    credito_minutos INTEGER NOT NULL DEFAULT 0,
    debito_minutos INTEGER NOT NULL DEFAULT 0,
    intervalo_minutos INTEGER NOT NULL DEFAULT 0,
    horas_normais_minutos INTEGER NOT NULL DEFAULT 0,
    horas_extras_1_minutos INTEGER NOT NULL DEFAULT 0,
    horas_extras_2_minutos INTEGER NOT NULL DEFAULT 0,
    adicional_noturno_minutos INTEGER NOT NULL DEFAULT 0,
    saldo_minutos INTEGER NOT NULL DEFAULT 0,
    motivo TEXT
);

CREATE INDEX IF NOT EXISTS ix_pt48_espelho_ponto_importacao_id ON pt48_espelho_ponto(importacao_id);
CREATE INDEX IF NOT EXISTS ix_pt48_espelho_ponto_colaborador_id ON pt48_espelho_ponto(colaborador_id);
CREATE INDEX IF NOT EXISTS ix_pt48_espelho_ponto_nome_normalizado ON pt48_espelho_ponto(nome_normalizado);
CREATE INDEX IF NOT EXISTS ix_pt48_espelho_ponto_data ON pt48_espelho_ponto(data);
