ALTER TABLE rp_timeline
    ADD COLUMN criado_por_supervisor_id INT NULL,
    ADD COLUMN alterado_por_usuario_id INT NULL;

ALTER TABLE rp_timeline
    ADD CONSTRAINT fk_rp_timeline_criador_supervisor
        FOREIGN KEY (criado_por_supervisor_id) REFERENCES supervisores(id),
    ADD CONSTRAINT fk_rp_timeline_alterador_usuario
        FOREIGN KEY (alterado_por_usuario_id) REFERENCES usuarios(id);
