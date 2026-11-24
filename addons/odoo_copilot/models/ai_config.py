# -*- coding: utf-8 -*-
"""
Modèle ai.config : configuration de la connexion au microservice FastAPI.
"""

from odoo import models, fields


class AiConfig(models.Model):
    """Configuration du microservice IA (URL et clé API)."""

    _name = 'ai.config'
    _description = 'Configuration du microservice IA'

    name = fields.Char(
        string='Nom',
        required=True,
        help='Nom de la configuration.',
    )
    service_url = fields.Char(
        string='URL du microservice',
        default='http://localhost:8001',
        help='URL de base du microservice FastAPI.',
    )
    service_api_key = fields.Char(
        string='Clé API du microservice',
        help='Clé API pour authentifier les appels vers le microservice.',
    )
    active = fields.Boolean(
        string='Actif',
        default=True,
        help='Seule la configuration active est utilisée.',
    )

    @classmethod
    def get_active_config(cls):
        """Retourne la première configuration active.

        Returns:
            recordset: Enregistrement ai.config actif, ou recordset vide.
        """
        return cls.search([('active', '=', True)], limit=1)
