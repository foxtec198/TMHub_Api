from utils.db import db
from models.base_model import BaseModel

class CostCenters(BaseModel):
    __tablename__ = "centro_de_custo"

    id = db.Column(db.Integer, primary_key=True)
    local = db.Column(db.String)
    departamento = db.Column(db.Integer)
    supervisor_id = db.Column(db.Integer)
    cidade_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "cidades.id",
            ondelete="SET NULL"
        )
    )
    valor_diaria_glosa = db.Column(db.Numeric(12, 2), nullable=True)
    filiais = db.relationship("Branch", secondary="filial_centros_custo", back_populates="centros_custo")
