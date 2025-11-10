// Sistema de Horarios con Telegram - JavaScript Principal

class HorariosTelegramApp {
    constructor() {
        this.currentUser = null;
        this.calendar = null;
        this.events = [];
        this.categories = [];
        this.settings = {};
        this.currentSection = 'calendar';
        this.editingEvent = null;
        this.editingCategory = null;
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.checkAuthentication();
        this.hideLoadingScreen();
    }

    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = e.target.closest('.nav-link').dataset.section;
                this.showSection(section);
            });
        });

        // Mobile menu
        document.getElementById('mobile-menu-toggle').addEventListener('click', () => {
            document.getElementById('nav-menu').classList.toggle('show');
        });

        // Authentication
        document.getElementById('google-login-btn').addEventListener('click', () => {
            this.loginWithGoogle();
        });

        document.getElementById('login-btn').addEventListener('click', () => {
            this.loginWithGoogle();
        });

        document.getElementById('logout-btn').addEventListener('click', () => {
            this.logout();
        });

        // Events
        document.getElementById('add-event-btn').addEventListener('click', () => {
            this.showSection('events');
            this.resetEventForm();
        });

        document.getElementById('event-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveEvent();
        });

        document.getElementById('cancel-event-btn').addEventListener('click', () => {
            this.resetEventForm();
        });

        // Categories
        document.getElementById('add-category-btn').addEventListener('click', () => {
            this.showCategoryForm();
        });

        document.getElementById('category-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveCategory();
        });

        document.getElementById('cancel-category-btn').addEventListener('click', () => {
            this.hideCategoryForm();
        });

        document.getElementById('category-color').addEventListener('change', (e) => {
            document.querySelector('.color-preview').style.backgroundColor = e.target.value;
        });

        // Telegram
        document.getElementById('telegram-link-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.linkTelegram();
        });

        document.getElementById('test-notification-btn').addEventListener('click', () => {
            this.testTelegramNotification();
        });

        document.getElementById('unlink-telegram-btn').addEventListener('click', () => {
            this.unlinkTelegram();
        });

        // Settings
        document.getElementById('settings-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveSettings();
        });

        // Modal
        document.getElementById('modal-close').addEventListener('click', () => {
            this.hideModal();
        });

        document.getElementById('event-modal').addEventListener('click', (e) => {
            if (e.target.id === 'event-modal') {
                this.hideModal();
            }
        });
    }

    hideLoadingScreen() {
        setTimeout(() => {
            document.getElementById('loading-screen').classList.add('hidden');
        }, 1000);
    }

    async checkAuthentication() {
        try {
            const response = await fetch('/auth/check');
            const data = await response.json();
            
            if (data.authenticated) {
                await this.loadUserData();
                this.showAuthenticatedUI();
                await this.loadAppData();
            } else {
                this.showLoginUI();
            }
        } catch (error) {
            console.error('Error checking authentication:', error);
            this.showLoginUI();
        }
    }

    async loadUserData() {
        try {
            const response = await fetch('/auth/user');
            const data = await response.json();
            
            if (data.authenticated) {
                this.currentUser = data.user;
            }
        } catch (error) {
            console.error('Error loading user data:', error);
        }
    }

    showLoginUI() {
        document.getElementById('login-section').style.display = 'block';
        document.getElementById('user-info').style.display = 'none';
        document.getElementById('login-btn').style.display = 'block';
        
        // Hide all other sections
        document.querySelectorAll('.section:not(#login-section)').forEach(section => {
            section.style.display = 'none';
        });
    }

    showAuthenticatedUI() {
        document.getElementById('login-section').style.display = 'none';
        document.getElementById('user-info').style.display = 'flex';
        document.getElementById('login-btn').style.display = 'none';
        
        if (this.currentUser) {
            document.getElementById('user-name').textContent = this.currentUser.name;
            if (this.currentUser.picture) {
                document.getElementById('user-avatar').src = this.currentUser.picture;
            }
        }
        
        this.showSection(this.currentSection);
    }

    async loginWithGoogle() {
        window.location.href = '/auth/login';
    }

    async logout() {
        try {
            const response = await fetch('/auth/logout', {
                method: 'POST'
            });
            
            if (response.ok) {
                this.currentUser = null;
                this.showLoginUI();
                this.showNotification('Sesión cerrada exitosamente', 'success');
            }
        } catch (error) {
            console.error('Error logging out:', error);
            this.showNotification('Error al cerrar sesión', 'error');
        }
    }

    showSection(sectionName) {
        // Update navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        
        document.querySelector(`[data-section="${sectionName}"]`).classList.add('active');
        
        // Show section
        document.querySelectorAll('.section:not(#login-section)').forEach(section => {
            section.style.display = 'none';
        });
        
        document.getElementById(`${sectionName}-section`).style.display = 'block';
        this.currentSection = sectionName;
        
        // Load section-specific data
        switch (sectionName) {
            case 'calendar':
                this.initCalendar();
                break;
            case 'events':
                this.loadEvents();
                break;
            case 'categories':
                this.loadCategories();
                break;
            case 'telegram':
                this.loadTelegramStatus();
                break;
            case 'settings':
                this.loadSettings();
                break;
        }
    }

    async loadAppData() {
        await Promise.all([
            this.loadEvents(),
            this.loadCategories(),
            this.loadSettings(),
            this.loadTelegramStatus()
        ]);
    }

    // Calendar Methods
    initCalendar() {
        if (this.calendar) {
            return;
        }

        const calendarEl = document.getElementById('calendar');
        this.calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            locale: 'es',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay'
            },
            events: this.events.map(event => ({
                id: event.id,
                title: event.title,
                start: event.start_time,
                end: event.end_time,
                backgroundColor: event.category ? event.category.color : '#3498db',
                borderColor: event.category ? event.category.color : '#3498db'
            })),
            eventClick: (info) => {
                this.showEventDetails(info.event.id);
            },
            dateClick: (info) => {
                this.createEventAtDate(info.dateStr);
            },
            editable: true,
            eventDrop: (info) => {
                this.updateEventDates(info.event.id, info.event.start, info.event.end);
            },
            eventResize: (info) => {
                this.updateEventDates(info.event.id, info.event.start, info.event.end);
            }
        });

        this.calendar.render();
    }

    refreshCalendar() {
        if (this.calendar) {
            this.calendar.removeAllEvents();
            this.calendar.addEventSource(this.events.map(event => ({
                id: event.id,
                title: event.title,
                start: event.start_time,
                end: event.end_time,
                backgroundColor: event.category ? event.category.color : '#3498db',
                borderColor: event.category ? event.category.color : '#3498db'
            })));
        }
    }

    createEventAtDate(dateStr) {
        this.showSection('events');
        this.resetEventForm();
        
        const startDate = new Date(dateStr + 'T09:00');
        const endDate = new Date(dateStr + 'T10:00');
        
        document.getElementById('event-start').value = this.formatDateTimeLocal(startDate);
        document.getElementById('event-end').value = this.formatDateTimeLocal(endDate);
    }

    async updateEventDates(eventId, start, end) {
        try {
            const response = await fetch(`/api/events/${eventId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    start_time: start.toISOString(),
                    end_time: end.toISOString()
                })
            });

            if (response.ok) {
                await this.loadEvents();
                this.showNotification('Evento actualizado', 'success');
            } else {
                throw new Error('Error updating event');
            }
        } catch (error) {
            console.error('Error updating event dates:', error);
            this.showNotification('Error al actualizar evento', 'error');
            this.refreshCalendar();
        }
    }

    // Events Methods
    async loadEvents() {
        try {
            const response = await fetch('/api/events');
            const data = await response.json();
            
            if (response.ok) {
                this.events = data.events;
                this.refreshCalendar();
                this.renderEventsList();
                this.updateEventCategoryOptions();
            }
        } catch (error) {
            console.error('Error loading events:', error);
        }
    }

    renderEventsList() {
        const eventsList = document.getElementById('events-list');
        
        if (this.events.length === 0) {
            eventsList.innerHTML = '<p>No hay eventos próximos</p>';
            return;
        }

        const upcomingEvents = this.events
            .filter(event => new Date(event.start_time) >= new Date())
            .sort((a, b) => new Date(a.start_time) - new Date(b.start_time))
            .slice(0, 10);

        eventsList.innerHTML = upcomingEvents.map(event => {
            const startDate = new Date(event.start_time);
            const categoryColor = event.category ? event.category.color : '#3498db';
            
            return `
                <div class="event-item" onclick="app.showEventDetails(${event.id})" style="border-left-color: ${categoryColor}">
                    <div class="event-title">${event.title}</div>
                    <div class="event-time">
                        ${startDate.toLocaleDateString()} ${startDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                    </div>
                    ${event.category ? `<div class="event-category">${event.category.name}</div>` : ''}
                </div>
            `;
        }).join('');
    }

    resetEventForm() {
        this.editingEvent = null;
        document.getElementById('event-form').reset();
        document.getElementById('event-reminder').value = '30';
        
        // Set default times
        const now = new Date();
        const start = new Date(now.getTime() + 60 * 60 * 1000); // 1 hour from now
        const end = new Date(start.getTime() + 60 * 60 * 1000); // 1 hour duration
        
        document.getElementById('event-start').value = this.formatDateTimeLocal(start);
        document.getElementById('event-end').value = this.formatDateTimeLocal(end);
    }

    async saveEvent() {
        const formData = new FormData(document.getElementById('event-form'));
        const eventData = {
            title: formData.get('title'),
            description: formData.get('description'),
            start_time: formData.get('start_time'),
            end_time: formData.get('end_time'),
            category_id: formData.get('category_id') || null,
            reminder_minutes: parseInt(formData.get('reminder_minutes')) || 30
        };

        try {
            let response;
            if (this.editingEvent) {
                response = await fetch(`/api/events/${this.editingEvent.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(eventData)
                });
            } else {
                response = await fetch('/api/events', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(eventData)
                });
            }

            if (response.ok) {
                await this.loadEvents();
                this.resetEventForm();
                this.showNotification(
                    this.editingEvent ? 'Evento actualizado' : 'Evento creado', 
                    'success'
                );
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Error saving event');
            }
        } catch (error) {
            console.error('Error saving event:', error);
            this.showNotification('Error al guardar evento: ' + error.message, 'error');
        }
    }

    async showEventDetails(eventId) {
        const event = this.events.find(e => e.id == eventId);
        if (!event) return;

        const startDate = new Date(event.start_time);
        const endDate = new Date(event.end_time);

        document.getElementById('modal-title').textContent = event.title;
        document.getElementById('modal-body').innerHTML = `
            <div class="event-details">
                <p><strong>Descripción:</strong> ${event.description || 'Sin descripción'}</p>
                <p><strong>Inicio:</strong> ${startDate.toLocaleString()}</p>
                <p><strong>Fin:</strong> ${endDate.toLocaleString()}</p>
                <p><strong>Categoría:</strong> ${event.category ? event.category.name : 'Sin categoría'}</p>
                <p><strong>Recordatorio:</strong> ${event.reminder_minutes} minutos antes</p>
            </div>
        `;

        document.getElementById('modal-actions').innerHTML = `
            <button class="btn btn-primary" onclick="app.editEvent(${event.id})">
                <i class="fas fa-edit"></i> Editar
            </button>
            <button class="btn btn-danger" onclick="app.deleteEvent(${event.id})">
                <i class="fas fa-trash"></i> Eliminar
            </button>
        `;

        this.showModal();
    }

    editEvent(eventId) {
        const event = this.events.find(e => e.id == eventId);
        if (!event) return;

        this.editingEvent = event;
        this.showSection('events');
        this.hideModal();

        // Fill form with event data
        document.getElementById('event-title').value = event.title;
        document.getElementById('event-description').value = event.description || '';
        document.getElementById('event-start').value = this.formatDateTimeLocal(new Date(event.start_time));
        document.getElementById('event-end').value = this.formatDateTimeLocal(new Date(event.end_time));
        document.getElementById('event-category').value = event.category_id || '';
        document.getElementById('event-reminder').value = event.reminder_minutes;
    }

    async deleteEvent(eventId) {
        if (!confirm('¿Estás seguro de que quieres eliminar este evento?')) {
            return;
        }

        try {
            const response = await fetch(`/api/events/${eventId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                await this.loadEvents();
                this.hideModal();
                this.showNotification('Evento eliminado', 'success');
            } else {
                throw new Error('Error deleting event');
            }
        } catch (error) {
            console.error('Error deleting event:', error);
            this.showNotification('Error al eliminar evento', 'error');
        }
    }

    // Categories Methods
    async loadCategories() {
        try {
            const response = await fetch('/api/categories');
            const data = await response.json();
            
            if (response.ok) {
                this.categories = data.categories;
                this.renderCategoriesGrid();
                this.updateEventCategoryOptions();
            }
        } catch (error) {
            console.error('Error loading categories:', error);
        }
    }

    renderCategoriesGrid() {
        const categoriesGrid = document.getElementById('categories-grid');
        
        if (this.categories.length === 0) {
            categoriesGrid.innerHTML = '<p>No hay categorías creadas</p>';
            return;
        }

        categoriesGrid.innerHTML = this.categories.map(category => `
            <div class="category-item">
                <div class="category-actions">
                    <button class="btn btn-sm btn-primary" onclick="app.editCategory(${category.id})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="app.deleteCategory(${category.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
                <div class="category-color" style="background-color: ${category.color}"></div>
                <h4>${category.name}</h4>
            </div>
        `).join('');
    }

    updateEventCategoryOptions() {
        const categorySelect = document.getElementById('event-category');
        categorySelect.innerHTML = '<option value="">Sin categoría</option>';
        
        this.categories.forEach(category => {
            const option = document.createElement('option');
            option.value = category.id;
            option.textContent = category.name;
            categorySelect.appendChild(option);
        });
    }

    showCategoryForm() {
        document.getElementById('category-form-container').style.display = 'block';
        this.resetCategoryForm();
    }

    hideCategoryForm() {
        document.getElementById('category-form-container').style.display = 'none';
        this.editingCategory = null;
    }

    resetCategoryForm() {
        document.getElementById('category-form').reset();
        document.getElementById('category-color').value = '#3498db';
        document.querySelector('.color-preview').style.backgroundColor = '#3498db';
    }

    async saveCategory() {
        const formData = new FormData(document.getElementById('category-form'));
        const categoryData = {
            name: formData.get('name'),
            color: formData.get('color')
        };

        try {
            let response;
            if (this.editingCategory) {
                response = await fetch(`/api/categories/${this.editingCategory.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(categoryData)
                });
            } else {
                response = await fetch('/api/categories', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(categoryData)
                });
            }

            if (response.ok) {
                await this.loadCategories();
                this.hideCategoryForm();
                this.showNotification(
                    this.editingCategory ? 'Categoría actualizada' : 'Categoría creada', 
                    'success'
                );
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Error saving category');
            }
        } catch (error) {
            console.error('Error saving category:', error);
            this.showNotification('Error al guardar categoría: ' + error.message, 'error');
        }
    }

    editCategory(categoryId) {
        const category = this.categories.find(c => c.id == categoryId);
        if (!category) return;

        this.editingCategory = category;
        this.showCategoryForm();

        document.getElementById('category-name').value = category.name;
        document.getElementById('category-color').value = category.color;
        document.querySelector('.color-preview').style.backgroundColor = category.color;
    }

    async deleteCategory(categoryId) {
        if (!confirm('¿Estás seguro de que quieres eliminar esta categoría?')) {
            return;
        }

        try {
            const response = await fetch(`/api/categories/${categoryId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                await this.loadCategories();
                this.showNotification('Categoría eliminada', 'success');
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Error deleting category');
            }
        } catch (error) {
            console.error('Error deleting category:', error);
            this.showNotification('Error al eliminar categoría: ' + error.message, 'error');
        }
    }

    // Telegram Methods
    async loadTelegramStatus() {
        try {
            const response = await fetch('/api/telegram/status');
            const data = await response.json();
            
            if (response.ok) {
                this.renderTelegramStatus(data);
            }
        } catch (error) {
            console.error('Error loading Telegram status:', error);
        }
    }

    renderTelegramStatus(status) {
        const statusDiv = document.getElementById('telegram-status');
        const setupDiv = document.getElementById('telegram-setup');
        const controlsDiv = document.getElementById('telegram-controls');

        if (status.linked) {
            statusDiv.innerHTML = `
                <div class="status-connected">
                    <h3><i class="fas fa-check-circle"></i> Telegram Conectado</h3>
                    <p><strong>ID de Chat:</strong> ${status.telegram_chat_id}</p>
                    ${status.telegram_username ? `<p><strong>Usuario:</strong> ${status.telegram_username}</p>` : ''}
                    <p><strong>Notificaciones:</strong> ${status.notifications_enabled ? 'Activadas' : 'Desactivadas'}</p>
                    <p><strong>Resumen diario:</strong> ${status.daily_summary_enabled ? 'Activado' : 'Desactivado'}</p>
                </div>
            `;
            setupDiv.style.display = 'none';
            controlsDiv.style.display = 'block';
        } else {
            statusDiv.innerHTML = `
                <div class="status-disconnected">
                    <h3><i class="fas fa-exclamation-circle"></i> Telegram No Conectado</h3>
                    <p>Vincula tu cuenta de Telegram para recibir notificaciones.</p>
                </div>
            `;
            setupDiv.style.display = 'block';
            controlsDiv.style.display = 'none';
        }
    }

    async linkTelegram() {
        const formData = new FormData(document.getElementById('telegram-link-form'));
        const telegramData = {
            telegram_chat_id: formData.get('telegram_chat_id'),
            telegram_username: formData.get('telegram_username')
        };

        try {
            const response = await fetch('/api/telegram/link', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(telegramData)
            });

            if (response.ok) {
                await this.loadTelegramStatus();
                document.getElementById('telegram-link-form').reset();
                this.showNotification('Cuenta de Telegram vinculada exitosamente', 'success');
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Error linking Telegram');
            }
        } catch (error) {
            console.error('Error linking Telegram:', error);
            this.showNotification('Error al vincular Telegram: ' + error.message, 'error');
        }
    }

    async testTelegramNotification() {
        try {
            const response = await fetch('/api/telegram/test', {
                method: 'POST'
            });

            if (response.ok) {
                this.showNotification('Notificación de prueba enviada', 'success');
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Error sending test notification');
            }
        } catch (error) {
            console.error('Error sending test notification:', error);
            this.showNotification('Error al enviar notificación: ' + error.message, 'error');
        }
    }

    async unlinkTelegram() {
        if (!confirm('¿Estás seguro de que quieres desvincular tu cuenta de Telegram?')) {
            return;
        }

        try {
            const response = await fetch('/api/telegram/unlink', {
                method: 'POST'
            });

            if (response.ok) {
                await this.loadTelegramStatus();
                this.showNotification('Cuenta de Telegram desvinculada', 'success');
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Error unlinking Telegram');
            }
        } catch (error) {
            console.error('Error unlinking Telegram:', error);
            this.showNotification('Error al desvincular Telegram: ' + error.message, 'error');
        }
    }

    // Settings Methods
    async loadSettings() {
        try {
            const response = await fetch('/api/settings');
            const data = await response.json();
            
            if (response.ok) {
                this.settings = data.settings;
                this.populateSettingsForm();
            }
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    }

    populateSettingsForm() {
        if (!this.settings) return;

        document.getElementById('timezone').value = this.settings.timezone || 'UTC';
        document.getElementById('default-reminder').value = this.settings.default_reminder_minutes || 30;
        document.getElementById('notifications-enabled').checked = this.settings.notifications_enabled || false;
        document.getElementById('daily-summary-enabled').checked = this.settings.daily_summary_enabled || false;
        document.getElementById('daily-summary-time').value = this.settings.daily_summary_time || '08:00';
    }

    async saveSettings() {
        const formData = new FormData(document.getElementById('settings-form'));
        const settingsData = {
            timezone: formData.get('timezone'),
            default_reminder_minutes: parseInt(formData.get('default_reminder_minutes')),
            notifications_enabled: formData.has('notifications_enabled'),
            daily_summary_enabled: formData.has('daily_summary_enabled'),
            daily_summary_time: formData.get('daily_summary_time')
        };

        try {
            const response = await fetch('/api/settings', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settingsData)
            });

            if (response.ok) {
                this.settings = settingsData;
                this.showNotification('Configuración guardada', 'success');
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Error saving settings');
            }
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showNotification('Error al guardar configuración: ' + error.message, 'error');
        }
    }

    // Utility Methods
    formatDateTimeLocal(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        
        return `${year}-${month}-${day}T${hours}:${minutes}`;
    }

    showModal() {
        document.getElementById('event-modal').classList.add('show');
    }

    hideModal() {
        document.getElementById('event-modal').classList.remove('show');
    }

    showNotification(message, type = 'info') {
        const toast = document.getElementById('notification-toast');
        const icon = toast.querySelector('.toast-icon');
        const messageEl = toast.querySelector('.toast-message');

        // Set icon based on type
        switch (type) {
            case 'success':
                icon.className = 'toast-icon fas fa-check-circle';
                toast.className = 'notification-toast toast-success';
                break;
            case 'error':
                icon.className = 'toast-icon fas fa-exclamation-circle';
                toast.className = 'notification-toast toast-error';
                break;
            case 'warning':
                icon.className = 'toast-icon fas fa-exclamation-triangle';
                toast.className = 'notification-toast toast-warning';
                break;
            default:
                icon.className = 'toast-icon fas fa-info-circle';
                toast.className = 'notification-toast';
        }

        messageEl.textContent = message;
        toast.classList.add('show');

        setTimeout(() => {
            toast.classList.remove('show');
        }, 4000);
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new HorariosTelegramApp();
});