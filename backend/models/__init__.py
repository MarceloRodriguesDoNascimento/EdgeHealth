"""Model layer: one file per entity, all inheriting the CRUD of models.base.BaseModel."""
from .base import BaseModel, DecimalText, iso, utcnow
from .empresa import Empresa
from .usuario import Usuario
from .auth_session import AuthSession
from .login_attempt import LoginAttempt
from .coletor import Coletor
from .dispositivo import Dispositivo
from .metrica import Metrica
from .falha import Falha
from .impacto import Impacto
from .diagnostico import Diagnostico
from .recomendacao import Recomendacao
from .diagnostico_recomendacao import DiagnosticoRecomendacao
from .registro_legado import RegistroLegado

__all__ = ['BaseModel', 'DecimalText', 'iso', 'utcnow', 'Empresa', 'Usuario', 'AuthSession', 'LoginAttempt',
           'Coletor', 'Dispositivo', 'Metrica', 'Falha', 'Impacto', 'Diagnostico', 'Recomendacao',
           'DiagnosticoRecomendacao', 'RegistroLegado']
