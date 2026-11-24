{
    'name': 'Odoo Copilot',
    'version': '20.0.2.0.0',
    'summary': 'Assistant IA multi-agents intégré à Odoo',
    'author': 'OdooCopilot',
    'category': 'Tools',
    'depends': ['base', 'mail', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/ai_config_data.xml',
        'views/ai_action_log_views.xml',
        'views/ai_config_views.xml',
        'views/copilot_chat_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odoo_copilot/static/src/copilot_chat_panel.css',
            'odoo_copilot/static/src/copilot_chat_panel.xml',
            'odoo_copilot/static/src/copilot_chat_panel.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
