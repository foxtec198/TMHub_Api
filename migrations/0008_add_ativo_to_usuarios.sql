-- Migration: Adicionar campo ativo aos usuários
-- Description: Adiciona coluna ativo na tabela usuarios com default TRUE

-- Adicionar coluna ativo
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE;

-- Criar índice
CREATE INDEX IF NOT EXISTS idx_usuarios_ativo ON usuarios(ativo);

-- Comment
COMMENT ON COLUMN usuarios.ativo IS 'Indica se o usuário está ativo (não pode acessar se inativo)';

-- Atualizar usuários existentes para ativos
UPDATE usuarios SET ativo = TRUE WHERE ativo IS NULL;
