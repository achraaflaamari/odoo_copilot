{
    'name': 'Odoo Copilot',
    'version': '20.0.1.0.0',
    'summary': 'Assistant IA multi-agents intégré à Odoo',
    'author': 'OdooCopilot',
    'category': 'Tools',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ai_config_data.xml',
        'views/ai_action_log_views.xml',
        'views/ai_config_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
