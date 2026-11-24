/** @odoo-module **/
/**
 * Composant OWL : Panneau de chat OdooCopilot.
 * Permet à l'utilisateur de poser des questions en langage naturel,
 * d'afficher les réponses des agents IA et d'approuver / rejeter les brouillons.
 */

import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

export class CopilotChatPanel extends Component {
    static template = "odoo_copilot.CopilotChatPanel";
    static props = {};

    setup() {
        this.notification = useService("notification");
        this.messagesRef = useRef("messages");

        this.state = useState({
            messages: [],       // { role: "user"|"agent", text, agent, status, draft_id, loading }
            input: "",
            loading: false,
            error: null,
        });
    }

    /**
     * Envoie la question au microservice via le contrôleur Odoo.
     */
    async sendMessage() {
        const question = this.state.input.trim();
        if (!question || this.state.loading) return;

        // Ajouter le message utilisateur
        this.state.messages.push({ role: "user", text: question });
        this.state.input = "";
        this.state.loading = true;
        this.state.error = null;

        // Message de chargement
        const loadingIdx = this.state.messages.length;
        this.state.messages.push({ role: "agent", text: "…", loading: true });

        this._scrollBottom();

        try {
            const result = await rpc("/copilot/chat", {
                question,
                user_id: odoo.info?.uid ?? 1,
            });

            // Remplacer le message de chargement par la vraie réponse
            this.state.messages[loadingIdx] = {
                role: "agent",
                text: result.answer,
                agent: result.agent,
                status: result.status,
                draft_id: result.draft_id ?? null,
                loading: false,
            };
        } catch (err) {
            this.state.messages[loadingIdx] = {
                role: "agent",
                text: "Erreur de connexion au service IA. Vérifiez que le microservice est démarré.",
                agent: "erreur",
                status: "error",
                loading: false,
            };
            this.state.error = err.message ?? "Erreur inconnue";
        } finally {
            this.state.loading = false;
            this._scrollBottom();
        }
    }

    /**
     * Approuve un brouillon d'action.
     * @param {string} draft_id - Identifiant unique du brouillon.
     */
    async approveDraft(draft_id) {
        try {
            const result = await rpc("/copilot/approve", { draft_id });
            this.notification.add(result.message ?? "Action approuvée.", { type: "success" });
            // Marquer le message comme approuvé
            this._updateDraftStatus(draft_id, "approved");
        } catch (err) {
            this.notification.add("Erreur lors de l'approbation.", { type: "danger" });
        }
    }

    /**
     * Rejette un brouillon d'action.
     * @param {string} draft_id - Identifiant unique du brouillon.
     */
    async rejectDraft(draft_id) {
        try {
            const result = await rpc("/copilot/reject", { draft_id });
            this.notification.add(result.message ?? "Action rejetée.", { type: "warning" });
            this._updateDraftStatus(draft_id, "rejected");
        } catch (err) {
            this.notification.add("Erreur lors du rejet.", { type: "danger" });
        }
    }

    /**
     * Gestion de la touche Entrée dans le champ de saisie.
     * @param {KeyboardEvent} ev
     */
    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }

    // ─────────────────────────── Méthodes privées ───────────────────────────

    _scrollBottom() {
        const el = this.messagesRef.el;
        if (el) el.scrollTop = el.scrollHeight;
    }

    _updateDraftStatus(draft_id, newStatus) {
        const msg = this.state.messages.find((m) => m.draft_id === draft_id);
        if (msg) msg.status = newStatus;
    }
}

// Enregistrement du composant dans le registre d'actions systématiques
registry.category("actions").add("odoo_copilot.chat_panel", CopilotChatPanel);
