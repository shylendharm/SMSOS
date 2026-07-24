// SMSOS v2 - Dashboard Client Application

const API_BASE = '/api/v1';

// State Management
const state = {
  token: localStorage.getItem('smsos_token') || null,
  user: null,
  currentRoute: 'orders',
  orders: [],
  catalog: [],
  customers: [],
  reservations: [],
  conversations: [],
  analytics: {},
};

// Toast Notifications
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <i data-lucide="${type === 'success' ? 'check-circle' : 'alert-circle'}"></i>
    <span>${message}</span>
  `;
  container.appendChild(toast);
  lucide.createIcons();

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// API Helper
async function api(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}),
    ...options.headers,
  };

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    if (res.status === 401 && endpoint !== '/auth/login') {
      logout();
      showToast('Session expired. Please log in again.', 'error');
      throw new Error('Unauthorized');
    }
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || data.error?.message || 'API Request Failed');
    }
    return data;
  } catch (err) {
    loggerError(err.message);
    throw err;
  }
}

function loggerError(msg) {
  console.error('[SMSOS Dashboard]', msg);
}

// Auth Handlers
function initAuth() {
  const loginForm = document.getElementById('login-form');
  const authScreen = document.getElementById('auth-screen');
  const appScreen = document.getElementById('app');

  if (state.token) {
    authScreen.style.display = 'none';
    appScreen.style.display = 'flex';
    initRouter();
  } else {
    authScreen.style.display = 'flex';
    appScreen.style.display = 'none';
  }

  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    try {
      const data = await api('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      state.token = data.access_token;
      localStorage.setItem('smsos_token', state.token);
      showToast('Logged in successfully!');
      authScreen.style.display = 'none';
      appScreen.style.display = 'flex';
      initRouter();
    } catch (err) {
      showToast(err.message || 'Login failed. Check credentials.', 'error');
    }
  });

  document.getElementById('logout-btn').addEventListener('click', logout);
}

function logout() {
  state.token = null;
  localStorage.removeItem('smsos_token');
  document.getElementById('auth-screen').style.display = 'flex';
  document.getElementById('app').style.display = 'none';
}

// Router
function initRouter() {
  window.addEventListener('hashchange', handleRoute);
  handleRoute();
}

function handleRoute() {
  const hash = window.location.hash.replace('#', '') || 'orders';
  state.currentRoute = hash;

  // Update sidebar active link
  document.querySelectorAll('.nav-item').forEach((item) => {
    if (item.dataset.route === hash) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  renderView(hash);
}

// Render Core Views
async function renderView(route) {
  const mainView = document.getElementById('main-view');
  const pageTitle = document.getElementById('page-title');
  const pageSubtitle = document.getElementById('page-subtitle');
  const headerActions = document.getElementById('header-actions');

  mainView.innerHTML = '<div style="padding:2rem; text-align:center;">Loading...</div>';

  try {
    switch (route) {
      case 'orders':
        pageTitle.innerText = 'Orders Management';
        pageSubtitle.innerText = 'Track incoming SMS & WhatsApp customer orders';
        headerActions.innerHTML = `<button class="btn btn-primary" onclick="openCreateOrderModal()"><i data-lucide="plus"></i> Create Order</button>`;
        await renderOrdersView(mainView);
        break;

      case 'catalog':
        pageTitle.innerText = 'Product & Service Catalog';
        pageSubtitle.innerText = 'Manage items and prices accessible by AI';
        headerActions.innerHTML = `<button class="btn btn-primary" onclick="openCreateCatalogModal()"><i data-lucide="plus"></i> Add Item</button>`;
        await renderCatalogView(mainView);
        break;

      case 'customers':
        pageTitle.innerText = 'Customer Directory';
        pageSubtitle.innerText = 'Customer details, phone contacts, and order histories';
        headerActions.innerHTML = `<button class="btn btn-primary" onclick="openCreateCustomerModal()"><i data-lucide="plus"></i> Add Customer</button>`;
        await renderCustomersView(mainView);
        break;

      case 'reservations':
        pageTitle.innerText = 'Reservations & Bookings';
        pageSubtitle.innerText = 'Table reservations and appointment slots';
        headerActions.innerHTML = `<button class="btn btn-primary" onclick="openCreateReservationModal()"><i data-lucide="plus"></i> New Reservation</button>`;
        await renderReservationsView(mainView);
        break;

      case 'conversations':
        pageTitle.innerText = 'AI WhatsApp Conversations';
        pageSubtitle.innerText = 'Live chat histories between Gemini AI and customers';
        headerActions.innerHTML = ``;
        await renderConversationsView(mainView);
        break;

      case 'analytics':
        pageTitle.innerText = 'Business Analytics';
        pageSubtitle.innerText = 'Revenue growth, top items, and conversation metrics';
        headerActions.innerHTML = ``;
        await renderAnalyticsView(mainView);
        break;

      default:
        window.location.hash = '#orders';
    }
  } catch (err) {
    mainView.innerHTML = `<div class="glass-panel" style="padding:2rem; color:var(--accent-rose);">Failed to load view: ${err.message}</div>`;
  }

  lucide.createIcons();
}

// ----------------------------------------------------
// ORDERS VIEW (PHASE 5)
// ----------------------------------------------------
async function renderOrdersView(container) {
  const orders = await api('/orders');
  state.orders = orders;

  const totalOrders = orders.length;
  const pendingCount = orders.filter((o) => o.status === 'pending').length;
  const totalRevenue = orders.reduce((acc, o) => acc + (parseFloat(o.total_amount) || 0), 0);

  container.innerHTML = `
    <div class="stats-grid">
      <div class="glass-panel stat-card">
        <div class="stat-icon" style="background: rgba(99, 102, 241, 0.2); color: var(--primary);">
          <i data-lucide="shopping-bag"></i>
        </div>
        <div class="stat-info">
          <div class="value">${totalOrders}</div>
          <div class="label">Total Orders</div>
        </div>
      </div>
      <div class="glass-panel stat-card">
        <div class="stat-icon" style="background: rgba(245, 158, 11, 0.2); color: var(--accent-amber);">
          <i data-lucide="clock"></i>
        </div>
        <div class="stat-info">
          <div class="value">${pendingCount}</div>
          <div class="label">Pending Orders</div>
        </div>
      </div>
      <div class="glass-panel stat-card">
        <div class="stat-icon" style="background: rgba(16, 185, 129, 0.2); color: var(--accent-emerald);">
          <i data-lucide="indian-rupee"></i>
        </div>
        <div class="stat-info">
          <div class="value">₹${totalRevenue.toFixed(2)}</div>
          <div class="label">Total Sales</div>
        </div>
      </div>
    </div>

    <div class="glass-panel" style="padding: 1.25rem;">
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Order Ref</th>
              <th>Channel</th>
              <th>Customer</th>
              <th>Items</th>
              <th>Total Amount</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${orders.length === 0 ? '<tr><td colspan="7" style="text-align:center; padding:2rem;">No orders found</td></tr>' : ''}
            ${orders.map((o) => `
              <tr>
                <td><strong>${o.order_number}</strong></td>
                <td><span class="badge badge-channel">${o.channel || 'whatsapp'}</span></td>
                <td>${o.customer_name || o.customer_phone || 'Customer'}</td>
                <td>${(o.items || []).map((i) => `${i.quantity}x ${i.item_name}`).join(', ') || 'N/A'}</td>
                <td><strong>₹${parseFloat(o.total_amount || 0).toFixed(2)}</strong></td>
                <td><span class="badge badge-${o.status}">${o.status}</span></td>
                <td>
                  ${o.status === 'pending' ? `
                    <button class="btn btn-secondary" style="padding:0.3rem 0.6rem; font-size:0.8rem;" onclick="updateOrderStatus('${o.id}', 'ready')">Mark Ready</button>
                  ` : ''}
                  ${o.status === 'ready' ? `
                    <button class="btn btn-secondary" style="padding:0.3rem 0.6rem; font-size:0.8rem; background:rgba(16,185,129,0.2);" onclick="updateOrderStatus('${o.id}', 'completed')">Complete</button>
                  ` : ''}
                  ${o.status !== 'completed' && o.status !== 'cancelled' ? `
                    <button class="btn-icon" style="color:var(--accent-rose);" title="Cancel Order" onclick="updateOrderStatus('${o.id}', 'cancelled')"><i data-lucide="x-circle"></i></button>
                  ` : ''}
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

async function updateOrderStatus(orderId, status) {
  try {
    await api(`/orders/${orderId}`, {
      method: 'PUT',
      body: JSON.stringify({ status }),
    });
    showToast(`Order status updated to ${status}!`);
    renderView('orders');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function openCreateOrderModal() {
  openModal('Create Manual Order', `
    <div class="form-group">
      <label>Customer Name</label>
      <input id="modal-order-name" class="form-control" placeholder="e.g. Anand" required>
    </div>
    <div class="form-group">
      <label>Phone Number</label>
      <input id="modal-order-phone" class="form-control" placeholder="+919876543210" required>
    </div>
    <div class="form-group">
      <label>Item Name</label>
      <input id="modal-order-item" class="form-control" placeholder="e.g. Masala Dosa" required>
    </div>
    <div class="form-group">
      <label>Unit Price (₹)</label>
      <input id="modal-order-price" type="number" class="form-control" placeholder="80" required>
    </div>
  `, async () => {
    const customer_name = document.getElementById('modal-order-name').value;
    const customer_phone = document.getElementById('modal-order-phone').value;
    const item_name = document.getElementById('modal-order-item').value;
    const unit_price = parseFloat(document.getElementById('modal-order-price').value);

    await api('/orders', {
      method: 'POST',
      body: JSON.stringify({
        customer_name,
        customer_phone,
        items: [{ item_name, quantity: 1, unit_price }],
      }),
    });
    showToast('Order created successfully!');
    renderView('orders');
  });
}

// ----------------------------------------------------
// CATALOG VIEW (PHASE 5)
// ----------------------------------------------------
async function renderCatalogView(container) {
  const items = await api('/catalog');
  state.catalog = items;

  container.innerHTML = `
    <div class="glass-panel" style="padding: 1.25rem;">
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Item Name</th>
              <th>Category</th>
              <th>Price</th>
              <th>Unit</th>
              <th>Availability</th>
            </tr>
          </thead>
          <tbody>
            ${items.length === 0 ? '<tr><td colspan="5" style="text-align:center; padding:2rem;">No items in catalog</td></tr>' : ''}
            ${items.map((item) => `
              <tr>
                <td><strong>${item.name}</strong></td>
                <td>${item.category || 'General'}</td>
                <td>₹${parseFloat(item.price).toFixed(2)}</td>
                <td>${item.unit || 'pcs'}</td>
                <td>
                  <span class="badge badge-${item.is_available ? 'active' : 'cancelled'}">
                    ${item.is_available ? 'In Stock' : 'Out of Stock'}
                  </span>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function openCreateCatalogModal() {
  openModal('Add Catalog Item', `
    <div class="form-group">
      <label>Item Name</label>
      <input id="modal-cat-name" class="form-control" placeholder="Coffee" required>
    </div>
    <div class="form-group">
      <label>Price (₹)</label>
      <input id="modal-cat-price" type="number" step="0.01" class="form-control" placeholder="40.00" required>
    </div>
    <div class="form-group">
      <label>Category</label>
      <input id="modal-cat-category" class="form-control" placeholder="Beverages">
    </div>
    <div class="form-group">
      <label>Unit</label>
      <input id="modal-cat-unit" class="form-control" placeholder="cup">
    </div>
  `, async () => {
    const name = document.getElementById('modal-cat-name').value;
    const price = parseFloat(document.getElementById('modal-cat-price').value);
    const category = document.getElementById('modal-cat-category').value;
    const unit = document.getElementById('modal-cat-unit').value;

    await api('/catalog', {
      method: 'POST',
      body: JSON.stringify({ name, price, category, unit }),
    });
    showToast('Catalog item added!');
    renderView('catalog');
  });
}

// ----------------------------------------------------
// CUSTOMERS VIEW (PHASE 5)
// ----------------------------------------------------
async function renderCustomersView(container) {
  const customers = await api('/customers');
  state.customers = customers;

  container.innerHTML = `
    <div class="glass-panel" style="padding: 1.25rem;">
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Phone Number</th>
              <th>Created At</th>
            </tr>
          </thead>
          <tbody>
            ${customers.length === 0 ? '<tr><td colspan="3" style="text-align:center; padding:2rem;">No customers found</td></tr>' : ''}
            ${customers.map((c) => `
              <tr>
                <td><strong>${c.name || 'Anonymous'}</strong></td>
                <td>${c.phone_number}</td>
                <td>${new Date(c.created_at).toLocaleDateString()}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function openCreateCustomerModal() {
  openModal('Add Customer', `
    <div class="form-group">
      <label>Name</label>
      <input id="modal-cust-name" class="form-control" placeholder="Customer Name" required>
    </div>
    <div class="form-group">
      <label>Phone Number</label>
      <input id="modal-cust-phone" class="form-control" placeholder="+919876543210" required>
    </div>
  `, async () => {
    const name = document.getElementById('modal-cust-name').value;
    const phone_number = document.getElementById('modal-cust-phone').value;

    await api('/customers', {
      method: 'POST',
      body: JSON.stringify({ name, phone_number }),
    });
    showToast('Customer added!');
    renderView('customers');
  });
}

// ----------------------------------------------------
// RESERVATIONS VIEW (PHASE 5)
// ----------------------------------------------------
async function renderReservationsView(container) {
  const reservations = await api('/reservations');
  state.reservations = reservations;

  container.innerHTML = `
    <div class="glass-panel" style="padding: 1.25rem;">
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Customer</th>
              <th>Party Size</th>
              <th>Table/Slot</th>
              <th>Reserved Date/Time</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${reservations.length === 0 ? '<tr><td colspan="5" style="text-align:center; padding:2rem;">No reservations found</td></tr>' : ''}
            ${reservations.map((r) => `
              <tr>
                <td><strong>${r.customer_name || 'Guest'}</strong></td>
                <td>${r.party_size} People</td>
                <td>${r.table_or_slot || 'General'}</td>
                <td>${new Date(r.reserved_at).toLocaleString()}</td>
                <td><span class="badge badge-${r.status}">${r.status}</span></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function openCreateReservationModal() {
  openModal('New Reservation', `
    <div class="form-group">
      <label>Customer Name</label>
      <input id="modal-res-name" class="form-control" placeholder="Jane Doe" required>
    </div>
    <div class="form-group">
      <label>Phone</label>
      <input id="modal-res-phone" class="form-control" placeholder="+919876543210" required>
    </div>
    <div class="form-group">
      <label>Party Size</label>
      <input id="modal-res-party" type="number" class="form-control" value="2" required>
    </div>
    <div class="form-group">
      <label>Date & Time</label>
      <input id="modal-res-time" type="datetime-local" class="form-control" required>
    </div>
  `, async () => {
    const customer_name = document.getElementById('modal-res-name').value;
    const customer_phone = document.getElementById('modal-res-phone').value;
    const party_size = parseInt(document.getElementById('modal-res-party').value);
    const reserved_at = new Date(document.getElementById('modal-res-time').value).toISOString();

    await api('/reservations', {
      method: 'POST',
      body: JSON.stringify({ customer_name, customer_phone, party_size, reserved_at }),
    });
    showToast('Reservation created!');
    renderView('reservations');
  });
}

// ----------------------------------------------------
// CONVERSATIONS VIEW (PHASE 6)
// ----------------------------------------------------
let activeThreadPhone = null;

async function renderConversationsView(container) {
  const threads = await api('/conversations');
  state.conversations = threads;

  if (threads.length > 0 && !activeThreadPhone) {
    activeThreadPhone = threads[0].phone_number;
  }

  const selectedThread = threads.find((t) => t.phone_number === activeThreadPhone) || threads[0];

  container.innerHTML = `
    <div class="chat-container">
      <!-- Left Thread List -->
      <div class="glass-panel chat-sidebar">
        <h3 style="font-size: 1.1rem; margin-bottom: 0.5rem;">Active Conversations</h3>
        <div class="thread-list">
          ${threads.length === 0 ? '<div style="text-align:center; padding:2rem; color:var(--text-subtle);">No active messages</div>' : ''}
          ${threads.map((t) => `
            <div class="thread-item ${t.phone_number === activeThreadPhone ? 'active' : ''}" onclick="selectChatThread('${t.phone_number}')">
              <div class="avatar" style="width:36px; height:36px; font-size:0.85rem;">${(t.customer_name || 'C')[0]}</div>
              <div class="thread-info">
                <div class="name">
                  <span>${t.customer_name || 'Customer'}</span>
                  <span style="font-size:0.7rem; color:var(--text-subtle);">${new Date(t.last_updated).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                </div>
                <div class="preview">${t.last_message || 'No messages'}</div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>

      <!-- Right Chat Drawer -->
      <div class="glass-panel chat-main">
        ${selectedThread ? `
          <div class="chat-header">
            <div>
              <h3 style="font-size: 1.15rem;">${selectedThread.customer_name}</h3>
              <span style="font-size: 0.8rem; color: var(--text-muted);">${selectedThread.phone_number}</span>
            </div>
            <span class="badge badge-channel">WhatsApp AI Chat</span>
          </div>

          <div class="chat-messages" id="chat-messages-container">
            ${(selectedThread.messages || []).map((m) => `
              <div class="message-bubble ${m.direction}">
                <div>${m.body}</div>
                <div class="message-time">
                  ${new Date(m.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                  ${m.direction === 'outbound' ? ' ✓✓' : ''}
                </div>
              </div>
            `).join('')}
          </div>
        ` : `
          <div style="display:flex; align-items:center; justify-content:center; height:100%; color:var(--text-muted);">
            Select a conversation thread to inspect
          </div>
        `}
      </div>
    </div>
  `;

  // Scroll chat messages to bottom
  const msgContainer = document.getElementById('chat-messages-container');
  if (msgContainer) {
    msgContainer.scrollTop = msgContainer.scrollHeight;
  }
}

function selectChatThread(phone) {
  activeThreadPhone = phone;
  renderView('conversations');
}

// ----------------------------------------------------
// ANALYTICS VIEW (PHASE 6)
// ----------------------------------------------------
async function renderAnalyticsView(container) {
  const analytics = await api('/analytics/summary');

  const rev = parseFloat(analytics.total_revenue || 0);
  const totalOrders = analytics.total_orders || 0;
  const pendingOrders = analytics.pending_orders || 0;
  const totalReservations = analytics.total_reservations || 0;
  const lowStock = analytics.low_stock_items_count || 0;
  const customers = analytics.total_customers || 0;

  const completedOrders = Math.max(0, totalOrders - pendingOrders);
  const completionRate = totalOrders > 0 ? ((completedOrders / totalOrders) * 100).toFixed(0) : 100;

  container.innerHTML = `
    <div class="stats-grid">
      <div class="glass-panel stat-card">
        <div class="stat-icon" style="background: rgba(16, 185, 129, 0.2); color: var(--accent-emerald);">
          <i data-lucide="indian-rupee"></i>
        </div>
        <div class="stat-info">
          <div class="value">₹${rev.toFixed(2)}</div>
          <div class="label">Total Revenue</div>
        </div>
      </div>

      <div class="glass-panel stat-card">
        <div class="stat-icon" style="background: rgba(99, 102, 241, 0.2); color: var(--primary);">
          <i data-lucide="shopping-bag"></i>
        </div>
        <div class="stat-info">
          <div class="value">${totalOrders}</div>
          <div class="label">Total Orders</div>
        </div>
      </div>

      <div class="glass-panel stat-card">
        <div class="stat-icon" style="background: rgba(6, 182, 212, 0.2); color: var(--accent-cyan);">
          <i data-lucide="users"></i>
        </div>
        <div class="stat-info">
          <div class="value">${customers}</div>
          <div class="label">Active Customers</div>
        </div>
      </div>

      <div class="glass-panel stat-card">
        <div class="stat-icon" style="background: rgba(139, 92, 246, 0.2); color: var(--accent-purple);">
          <i data-lucide="calendar"></i>
        </div>
        <div class="stat-info">
          <div class="value">${totalReservations}</div>
          <div class="label">Confirmed Reservations</div>
        </div>
      </div>
    </div>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 1.5rem; margin-top: 1rem;">
      <div class="glass-panel chart-card">
        <h3>Order Fulfillment Breakdown</h3>
        <div>
          <div style="display:flex; justify-content:space-between; font-size:0.9rem;">
            <span>Completed Orders (${completedOrders})</span>
            <span>${completionRate}%</span>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width: ${completionRate}%; background: linear-gradient(90deg, var(--accent-emerald), var(--accent-cyan));"></div>
          </div>
        </div>

        <div>
          <div style="display:flex; justify-content:space-between; font-size:0.9rem;">
            <span>Pending Orders (${pendingOrders})</span>
            <span>${100 - completionRate}%</span>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width: ${100 - completionRate}%; background: linear-gradient(90deg, var(--accent-amber), var(--accent-rose));"></div>
          </div>
        </div>
      </div>

      <div class="glass-panel chart-card">
        <h3>Inventory & Operations Health</h3>
        <div style="display:flex; align-items:center; justify-content:space-between; padding: 0.75rem 0; border-bottom:1px solid var(--border-glass);">
          <span style="color:var(--text-muted);">Low Stock Alerts</span>
          <span class="badge ${lowStock > 0 ? 'badge-cancelled' : 'badge-completed'}">${lowStock} items low</span>
        </div>
        <div style="display:flex; align-items:center; justify-content:space-between; padding: 0.75rem 0;">
          <span style="color:var(--text-muted);">Primary AI Communication Channel</span>
          <span class="badge badge-channel">Twilio WhatsApp</span>
        </div>
      </div>
    </div>
  `;
}

// Modal helper
function openModal(title, contentHtml, onSubmit) {
  const modalRoot = document.getElementById('modal-root');
  modalRoot.innerHTML = `
    <div class="modal-card">
      <div class="modal-header">
        <h2>${title}</h2>
        <button class="btn-icon" onclick="closeModal()"><i data-lucide="x"></i></button>
      </div>
      <form id="modal-form">
        ${contentHtml}
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
          <button type="submit" class="btn btn-primary">Save Changes</button>
        </div>
      </form>
    </div>
  `;
  modalRoot.classList.add('active');
  lucide.createIcons();

  document.getElementById('modal-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await onSubmit();
      closeModal();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

function closeModal() {
  const modalRoot = document.getElementById('modal-root');
  modalRoot.classList.remove('active');
}

// Global Exports
window.openCreateOrderModal = openCreateOrderModal;
window.openCreateCatalogModal = openCreateCatalogModal;
window.openCreateCustomerModal = openCreateCustomerModal;
window.openCreateReservationModal = openCreateReservationModal;
window.updateOrderStatus = updateOrderStatus;
window.selectChatThread = selectChatThread;
window.closeModal = closeModal;

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', initAuth);
