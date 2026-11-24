# -*- coding: utf-8 -*-
"""
Modèle ai.action.log : journal des actions de l'assistant IA.
Chaque action proposée, approuvée, rejetée ou exécutée est enregistrée ici.
"""

from odoo import models, fields


class AiActionLog(models.Model):
    """Journal des actions IA avec validation humaine."""

    _name = 'ai.action.log'
    _description = 'Journal des actions de l\'assistant IA'
    _order = 'create_date desc'

    name = fields.Char(
        string='Résumé',
        required=True,
        help='Résumé court de l\'action proposée ou exécutée.',
    )
    question = fields.Text(
        string='Question',
        help='Question posée par l\'utilisateur.',
    )
    agent = fields.Selection(
        selection=[
            ('ventes', 'Ventes'),
            ('achats', 'Achats'),
            ('projets', 'Projets'),
            ('routeur', 'Routeur'),
        ],
        string='Agent',
        help='Agent IA ayant traité la demande.',
    )
    status = fields.Selection(
        selection=[
            ('draft', 'Brouillon'),
            ('approved', 'Approuvé'),
            ('rejected', 'Rejeté'),
            ('executed', 'Exécuté'),
        ],
        string='Statut',
        default='draft',
        help='Statut de l\'action dans le circuit de validation.',
    )
    draft_payload = fields.Text(
        string='Payload brouillon',
        help='Payload JSON de l\'action proposée, en attente de validation.',
    )
    response = fields.Text(
        string='Réponse',
        help='Réponse complète fournie par l\'agent.',
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Utilisateur',
        ondelete='set null',
        help='Utilisateur Odoo ayant posé la question.',
    )
    create_date = fields.Datetime(
        string='Date de création',
        readonly=True,
    )
