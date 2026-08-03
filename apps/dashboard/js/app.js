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
  inventory: [],
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

function showAuthCard(type) {
  const setVisible = (id, visible) => {
    const el = document.getElementById(id);
    if (el) el.style.display = visible ? 'block' : 'none';
  };
  setVisible('login-card', type === 'login');
  setVisible('signup-card', type === 'signup');
  setVisible('onboarding-card', type === 'onboarding');
}

async function loadUserProfile() {
  if (!state.token) return;
  try {
    const profile = await api('/auth/profile');
    state.user = profile;
    const nameEl = document.getElementById('user-name');
    const profileNameEl = document.getElementById('profile-user-name');
    const avatarEl = document.getElementById('user-avatar');
    if (nameEl) nameEl.innerText = profile.name || 'Owner';
    if (profileNameEl) profileNameEl.innerText = profile.name || 'Owner';
    if (avatarEl && profile.name) avatarEl.innerText = profile.name.charAt(0).toUpperCase();
  } catch (err) {
    loggerError('Failed to load user profile: ' + err.message);
  }
}

// Auth Handlers
function initAuth() {
  const loginForm = document.getElementById('login-form');
  const signupForm = document.getElementById('signup-form');
  const onboardingForm = document.getElementById('onboarding-form');
  const authScreen = document.getElementById('auth-screen');
  const appScreen = document.getElementById('app');

  if (state.token) {
    authScreen.style.display = 'none';
    appScreen.style.display = 'flex';
    loadUserProfile();
    initRouter();
  } else {
    authScreen.style.display = 'flex';
    appScreen.style.display = 'none';
    showAuthCard('login');
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
      await loadUserProfile();
      initRouter();
    } catch (err) {
      showToast(err.message || 'Login failed. Check credentials.', 'error');
    }
  });

  if (signupForm) {
    signupForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('signup-name').value;
      const email = document.getElementById('signup-email').value;
      const password = document.getElementById('signup-password').value;
      const business_name = document.getElementById('signup-biz-name').value;
      const phone_number = document.getElementById('signup-phone').value;
      const business_type = document.getElementById('signup-biz-type').value;
      const location = document.getElementById('signup-location').value;
      const default_prep_time_minutes = parseInt(document.getElementById('signup-prep-time').value) || 15;
      const delivery_radius_km = parseFloat(document.getElementById('signup-radius').value) || 10.0;

      try {
        const data = await api('/auth/register', {
          method: 'POST',
          body: JSON.stringify({
            name,
            email,
            password,
            business_name,
            phone_number,
            business_type,
            location,
            default_prep_time_minutes,
            delivery_radius_km,
          }),
        });
        state.token = data.access_token;
        localStorage.setItem('smsos_token', state.token);
        showToast('Shop created & registered successfully!');
        authScreen.style.display = 'none';
        appScreen.style.display = 'flex';
        await loadUserProfile();
        initRouter();
      } catch (err) {
        showToast(err.message || 'Registration failed.', 'error');
      }
    });
  }

  document.getElementById('logout-btn').addEventListener('click', confirmLogout);

  document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('profile-dropdown-menu');
    const menuBtn = document.getElementById('profile-menu-btn');
    if (dropdown && menuBtn && !menuBtn.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.style.display = 'none';
    }
  });
}

function toggleProfileDropdown() {
  const dropdown = document.getElementById('profile-dropdown-menu');
  if (dropdown) {
    dropdown.style.display = dropdown.style.display === 'flex' ? 'none' : 'flex';
  }
}

async function openProfileModal() {
  const dropdown = document.getElementById('profile-dropdown-menu');
  if (dropdown) dropdown.style.display = 'none';

  let profile = state.user;
  try {
    profile = await api('/auth/profile');
    state.user = profile;
  } catch (err) {}

  openModal('Edit Owner Profile', `
    <div class="form-group">
      <label>Full Name</label>
      <input id="modal-prof-name" class="form-control" value="${profile?.name || ''}" required>
    </div>
    <div class="form-group">
      <label>Email Address <span style="font-size:0.75rem; color:var(--text-muted);">(Unchangeable)</span></label>
      <input id="modal-prof-email" type="email" class="form-control" value="${profile?.email || ''}" disabled style="background: #f1f5f9; color: var(--text-muted); cursor: not-allowed;">
    </div>
    <div class="form-group">
      <label>Password <span style="font-size:0.75rem; color:var(--text-muted);">(Unchangeable)</span></label>
      <input id="modal-prof-pass" type="password" class="form-control" placeholder="••••••••" disabled style="background: #f1f5f9; color: var(--text-muted); cursor: not-allowed;">
    </div>
    <hr style="border-color: var(--border-color); margin: 1rem 0;">
    <div class="form-group">
      <label>Business Name</label>
      <input id="modal-prof-biz-name" class="form-control" value="${profile?.business_name || ''}" required>
    </div>
    <div class="form-group">
      <label>Shop Phone Number</label>
      <input id="modal-prof-phone" class="form-control" value="${profile?.phone_number || ''}" required>
    </div>
    <div class="form-group">
      <label>Shop Address / Location</label>
      <input id="modal-prof-location" class="form-control" value="${profile?.location || ''}">
    </div>
  `, async () => {
    const name = document.getElementById('modal-prof-name').value;
    const business_name = document.getElementById('modal-prof-biz-name').value;
    const phone_number = document.getElementById('modal-prof-phone').value;
    const location = document.getElementById('modal-prof-location').value;

    const body = { name, business_name, phone_number, location };

    await api('/auth/profile', {
      method: 'PUT',
      body: JSON.stringify(body),
    });

    showToast('Profile updated successfully!');
    await loadUserProfile();
  });
}

function confirmLogout() {
  const dropdown = document.getElementById('profile-dropdown-menu');
  if (dropdown) dropdown.style.display = 'none';

  openModal(
    'Confirm Sign Out',
    `
    <div style="text-align: center; padding: 0.5rem 0 1rem;">
      <div style="width: 52px; height: 52px; background: #fee2e2; color: var(--accent-rose); border-radius: var(--radius-full); display: inline-flex; align-items: center; justify-content: center; margin-bottom: 1rem; border: 1px solid #fecaca;">
        <i data-lucide="log-out" style="width: 24px; height: 24px;"></i>
      </div>
      <h3 style="font-size: 1.15rem; font-weight: 700; margin-bottom: 0.5rem; color: var(--text-main);">Are you sure you want to sign out?</h3>
      <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 0.5rem;">You will be logged out of your shop session and returned to the login screen.</p>
    </div>
    `,
    async () => {
      logout();
      showToast('Signed out successfully.');
    },
    'Sign Out',
    'btn-danger'
  );
}

function logout() {
  state.token = null;
  localStorage.removeItem('smsos_token');
  document.getElementById('auth-screen').style.display = 'flex';
  document.getElementById('app').style.display = 'none';
  showAuthCard('login');
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

  // Update mobile bottom nav active link
  document.querySelectorAll('.mobile-nav-item').forEach((item) => {
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

      case 'inventory':
        pageTitle.innerText = 'Inventory Management';
        pageSubtitle.innerText = 'Track stock levels, set thresholds, and manage supplies';
        headerActions.innerHTML = `<button class="btn btn-primary" onclick="openCreateInventoryModal()"><i data-lucide="plus"></i> Add Stock Item</button>`;
        await renderInventoryView(mainView);
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

      case 'analytics':
        pageTitle.innerText = 'Business Analytics';
        pageSubtitle.innerText = 'Revenue trends, top items, and performance metrics';
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

// ============================================================
// STATUS HELPERS
// ============================================================
const STATUS_CONFIG = {
  draft:                { label: 'Draft',            color: '#6b7280', bg: 'rgba(107,114,128,0.15)' },
  pending:              { label: 'Pending',          color: '#f59e0b', bg: 'rgba(245,158,11,0.15)' },
  pending_confirmation: { label: 'Awaiting Confirm', color: '#3b82f6', bg: 'rgba(59,130,246,0.15)' },
  confirmed:            { label: 'Confirmed',        color: '#10b981', bg: 'rgba(16,185,129,0.15)' },
  in_preparation:       { label: 'Preparing',        color: '#f97316', bg: 'rgba(249,115,22,0.15)' },
  out_for_delivery:     { label: 'Out for Delivery', color: '#8b5cf6', bg: 'rgba(139,92,246,0.15)' },
  ready:                { label: 'Ready',            color: '#06b6d4', bg: 'rgba(6,182,212,0.15)' },
  delivered:            { label: 'Delivered',         color: '#10b981', bg: 'rgba(16,185,129,0.20)' },
  completed:            { label: 'Completed',        color: '#10b981', bg: 'rgba(16,185,129,0.20)' },
  cancelled:            { label: 'Cancelled',        color: '#ef4444', bg: 'rgba(239,68,68,0.15)' },
};

function statusBadge(status) {
  const cfg = STATUS_CONFIG[status] || { label: status, color: '#6b7280', bg: 'rgba(107,114,128,0.15)' };
  const pulse = status === 'confirmed' ? 'animation: pulse 2s infinite;' : '';
  return `<span style="display:inline-block; padding:0.25rem 0.65rem; border-radius:20px; font-size:0.75rem; font-weight:600; color:${cfg.color}; background:${cfg.bg}; border:1px solid ${cfg.color}22; ${pulse}">${cfg.label}</span>`;
}

// ============================================================
// ORDERS VIEW
// ============================================================
let orderStatusFilter = 'all';

async function renderOrdersView(container) {
  const fetchStatus = orderStatusFilter === 'pending_confirmation' ? 'pending_confirmation' : (orderStatusFilter === 'all' ? 'all' : null);
  const orders = await api(fetchStatus ? `/orders?status=${fetchStatus}` : '/orders');
  state.orders = orders;

  const filtered = orderStatusFilter === 'all' 
    ? orders.filter(o => !['draft', 'pending_confirmation'].includes(o.status)) 
    : orders.filter(o => {
        if (orderStatusFilter === 'active') return !['delivered', 'completed', 'cancelled', 'draft', 'pending_confirmation'].includes(o.status);
        if (orderStatusFilter === 'delivered') return ['delivered', 'completed'].includes(o.status);
        return o.status === orderStatusFilter;
      });

  const totalOrders = orders.filter(o => !['draft', 'pending_confirmation'].includes(o.status)).length;
  const pendingCount = orders.filter((o) => !['delivered', 'completed', 'cancelled', 'draft', 'pending_confirmation'].includes(o.status)).length;
  const totalRevenue = orders.filter(o => !['draft', 'pending_confirmation'].includes(o.status)).reduce((acc, o) => acc + (parseFloat(o.total_amount) || 0), 0);

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
          <div class="label">Active Orders</div>
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

    <!-- Status Filter -->
    <div class="glass-panel" style="padding: 0.75rem 1.25rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
      <span style="font-size: 0.85rem; font-weight: 500; color: var(--text-muted); margin-right: 0.25rem;">Filter:</span>
      ${['all', 'active', 'confirmed', 'in_preparation', 'out_for_delivery', 'delivered', 'pending_confirmation', 'cancelled'].map(f => {
        const label = f === 'all' ? 'All' : f === 'active' ? 'Active' : (STATUS_CONFIG[f]?.label || f);
        const isActive = orderStatusFilter === f;
        return `<button class="btn ${isActive ? 'btn-primary' : ''}" style="padding:0.3rem 0.7rem; font-size:0.8rem;" onclick="orderStatusFilter='${f}'; renderView('orders');">${label}</button>`;
      }).join('')}
    </div>

    <div class="glass-panel" style="padding: 1.25rem;">
      <div class="table-container">
        <table class="data-table orders-table">
          <thead>
            <tr>
              <th>Order Ref</th>
              <th>Channel</th>
              <th>Items</th>
              <th>Delivery & ETA</th>
              <th>Total</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${filtered.length === 0 ? '<tr><td colspan="7" style="text-align:center; padding:2rem;">No orders found</td></tr>' : ''}
            ${filtered.map((o) => `
              <tr style="${o.status === 'confirmed' ? 'background: rgba(16,185,129,0.05);' : ''}">
                <td style="white-space:nowrap;"><strong>#${o.order_number}</strong></td>
                <td><span class="badge badge-channel" style="white-space:nowrap; text-transform:capitalize;">${o.channel || 'whatsapp'}</span></td>
                <td>${(o.items || []).map((i) => `${i.quantity}x ${i.item_name}`).join(', ') || 'N/A'}</td>
                <td style="white-space:nowrap;">
                  ${o.delivery_location ? `
                    <div style="font-weight:500;">📍 ${o.delivery_location}</div>
                    ${o.estimated_delivery_minutes ? `<small style="color:var(--accent-amber); display:block; margin-top:2px;">⏱️ ~${o.estimated_delivery_minutes} mins</small>` : ''}
                  ` : '<span style="color:var(--text-muted);">Self / Takeaway</span>'}
                </td>
                <td style="white-space:nowrap;"><strong>₹${parseFloat(o.total_amount || 0).toFixed(2)}</strong></td>
                <td style="white-space:nowrap;">${statusBadge(o.status)}</td>
                <td style="white-space:nowrap;">
                  <div style="display:flex; align-items:center; gap:0.4rem;">
                    ${['confirmed', 'pending', 'pending_confirmation', 'draft'].includes(o.status) ? `
                      <button class="btn btn-primary" style="padding:0.35rem 0.7rem; font-size:0.8rem; display:inline-flex; align-items:center; gap:0.25rem;" onclick="updateOrderStatus('${o.id}', 'in_preparation')">👨‍🍳 Prep</button>
                    ` : ''}
                    ${o.status === 'in_preparation' ? `
                      <button class="btn btn-secondary" style="padding:0.35rem 0.7rem; font-size:0.8rem; background:rgba(139,92,246,0.15); color:#8b5cf6; border:1px solid rgba(139,92,246,0.3); display:inline-flex; align-items:center; gap:0.25rem;" onclick="updateOrderStatus('${o.id}', 'out_for_delivery')">🛵 Dispatch</button>
                    ` : ''}
                    ${o.status === 'out_for_delivery' || o.status === 'ready' ? `
                      <button class="btn btn-secondary" style="padding:0.35rem 0.7rem; font-size:0.8rem; background:rgba(16,185,129,0.15); color:#10b981; border:1px solid rgba(16,185,129,0.3); display:inline-flex; align-items:center; gap:0.25rem;" onclick="updateOrderStatus('${o.id}', 'delivered')">📦 Delivered</button>
                    ` : ''}
                    ${!['delivered', 'completed', 'cancelled'].includes(o.status) ? `
                      <button class="btn-icon" style="color:var(--accent-amber);" title="Cancel Order" onclick="updateOrderStatus('${o.id}', 'cancelled')"><i data-lucide="x-circle"></i></button>
                    ` : ''}
                    <button class="btn-icon" style="color:var(--accent-rose);" title="Delete Order" onclick="deleteOrder('${o.id}')"><i data-lucide="trash-2"></i></button>
                  </div>
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
  const catalog = state.catalog || [];
  const datalistOptions = catalog.map(c => `<option value="${c.name}">₹${parseFloat(c.price).toFixed(2)}</option>`).join('');

  openModal('Create Manual Order', `
    <datalist id="catalog-items-datalist">
      ${datalistOptions}
    </datalist>

    <div style="display: flex; flex-direction: column; gap: 1rem;">
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
        <div class="form-group" style="margin: 0;">
          <label style="font-size: 0.85rem; font-weight: 600;">Customer Name</label>
          <input id="modal-order-name" class="form-control" placeholder="e.g. Anand" required>
        </div>
        <div class="form-group" style="margin: 0;">
          <label style="font-size: 0.85rem; font-weight: 600;">Phone Number</label>
          <input id="modal-order-phone" class="form-control" placeholder="+919876543210" required>
        </div>
      </div>

      <div class="form-group" style="margin: 0;">
        <label style="font-size: 0.85rem; font-weight: 600;">Delivery Address / Location (Optional)</label>
        <input id="modal-order-location" class="form-control" placeholder="e.g. Table 4 or Door Address">
      </div>

      <hr style="border-color: var(--border-color); margin: 0.25rem 0;">

      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
          <label style="font-weight: 700; font-size: 0.9rem; color: var(--text-main);">Order Items</label>
          <button type="button" class="btn btn-secondary" style="padding: 0.25rem 0.6rem; font-size: 0.775rem;" onclick="addManualOrderItemRow()">
            <i data-lucide="plus" style="width: 14px; height: 14px;"></i> Add Item
          </button>
        </div>

        <div style="display: grid; grid-template-columns: 2fr 1fr 1fr 32px; gap: 0.5rem; margin-bottom: 0.35rem; font-size: 0.75rem; font-weight: 600; color: var(--text-muted);">
          <div>Item Name</div>
          <div>Qty</div>
          <div>Price (₹)</div>
          <div></div>
        </div>

        <div id="modal-order-items-list" style="display: flex; flex-direction: column; gap: 0.5rem;">
          <!-- Item rows inserted here -->
        </div>
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center; background: var(--bg-page); padding: 0.75rem 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); margin-top: 0.5rem;">
        <span style="font-weight: 600; font-size: 0.9rem; color: var(--text-muted);">Estimated Total:</span>
        <span id="modal-order-total-display" style="font-size: 1.15rem; font-weight: 800; color: var(--primary);">₹0.00</span>
      </div>
    </div>
  `, async () => {
    const customer_name = document.getElementById('modal-order-name').value.trim();
    const customer_phone = document.getElementById('modal-order-phone').value.trim();
    const delivery_location = document.getElementById('modal-order-location').value.trim();

    const rowElements = document.querySelectorAll('.manual-order-item-row');
    const items = [];

    rowElements.forEach(row => {
      const item_name = row.querySelector('.order-item-name').value.trim();
      const quantity = parseInt(row.querySelector('.order-item-qty').value) || 1;
      const unit_price = parseFloat(row.querySelector('.order-item-price').value) || 0;

      if (item_name) {
        items.push({ item_name, quantity, unit_price });
      }
    });

    if (items.length === 0) {
      showToast('Please add at least one valid item to the order!', 'error');
      return;
    }

    await api('/orders', {
      method: 'POST',
      body: JSON.stringify({
        customer_name,
        customer_phone,
        delivery_location,
        items,
      }),
    });
    showToast('Order created successfully!');
    renderView('orders');
  });

  // Automatically insert initial item row
  addManualOrderItemRow();
}

window.addManualOrderItemRow = function(name = '', qty = 1, price = '') {
  const container = document.getElementById('modal-order-items-list');
  if (!container) return;

  const row = document.createElement('div');
  row.className = 'manual-order-item-row';
  row.style.cssText = 'display: grid; grid-template-columns: 2fr 1fr 1fr 32px; gap: 0.5rem; align-items: center;';

  row.innerHTML = `
    <input class="form-control order-item-name" list="catalog-items-datalist" placeholder="e.g. Masala Dosa" value="${name}" oninput="onManualItemNameChange(this)" required>
    <input type="number" min="1" class="form-control order-item-qty" value="${qty}" oninput="updateManualOrderTotal()" required>
    <input type="number" step="0.01" min="0" class="form-control order-item-price" placeholder="0" value="${price}" oninput="updateManualOrderTotal()" required>
    <button type="button" class="btn-icon" style="color: var(--accent-rose); height: 34px;" onclick="removeManualOrderItemRow(this)" title="Remove Item">
      <i data-lucide="trash-2" style="width: 16px; height: 16px;"></i>
    </button>
  `;

  container.appendChild(row);
  if (window.lucide) lucide.createIcons();
  updateManualOrderTotal();
};

window.removeManualOrderItemRow = function(btn) {
  const container = document.getElementById('modal-order-items-list');
  if (!container) return;
  if (container.children.length <= 1) {
    showToast('An order must have at least one item.', 'error');
    return;
  }
  btn.closest('.manual-order-item-row').remove();
  updateManualOrderTotal();
};

window.onManualItemNameChange = function(input) {
  const val = input.value.trim().toLowerCase();
  const catalog = state.catalog || [];
  const found = catalog.find(c => c.name.toLowerCase() === val);
  if (found) {
    const row = input.closest('.manual-order-item-row');
    const priceInput = row.querySelector('.order-item-price');
    if (priceInput && (!priceInput.value || parseFloat(priceInput.value) === 0)) {
      priceInput.value = found.price;
    }
  }
  updateManualOrderTotal();
};

window.updateManualOrderTotal = function() {
  const rows = document.querySelectorAll('.manual-order-item-row');
  let total = 0;
  rows.forEach(row => {
    const qty = parseFloat(row.querySelector('.order-item-qty')?.value) || 0;
    const price = parseFloat(row.querySelector('.order-item-price')?.value) || 0;
    total += qty * price;
  });
  const display = document.getElementById('modal-order-total-display');
  if (display) {
    display.innerText = `₹${total.toFixed(2)}`;
  }
};

// ============================================================
// CATALOG VIEW — Edit + Availability Toggle + Category Filter
// ============================================================
let catalogCategoryFilter = 'all';

async function renderCatalogView(container) {
  const items = await api('/catalog');
  state.catalog = items;

  // Extract unique categories
  const categories = [...new Set(items.map(i => i.category || 'General'))].sort();

  const filtered = catalogCategoryFilter === 'all'
    ? items
    : items.filter(i => (i.category || 'General') === catalogCategoryFilter);

  container.innerHTML = `
    <!-- Category Filter -->
    <div class="glass-panel" style="padding: 0.75rem 1.25rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
      <span style="font-size: 0.85rem; font-weight: 500; color: var(--text-muted); margin-right: 0.25rem;">Category:</span>
      <button class="btn ${catalogCategoryFilter === 'all' ? 'btn-primary' : ''}" style="padding:0.3rem 0.7rem; font-size:0.8rem;" onclick="catalogCategoryFilter='all'; renderView('catalog');">All</button>
      ${categories.map(cat => `
        <button class="btn ${catalogCategoryFilter === cat ? 'btn-primary' : ''}" style="padding:0.3rem 0.7rem; font-size:0.8rem;" onclick="catalogCategoryFilter='${cat}'; renderView('catalog');">${cat}</button>
      `).join('')}
    </div>

    <div class="glass-panel" style="padding: 1.25rem;">
      <div class="table-container">
        <table class="data-table catalog-table">
          <thead>
            <tr>
              <th>Item Name</th>
              <th>Category</th>
              <th>Price</th>
              <th>Unit</th>
              <th>Availability</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${filtered.length === 0 ? '<tr><td colspan="6" style="text-align:center; padding:2rem;">No items in catalog</td></tr>' : ''}
            ${filtered.map((item) => `
              <tr style="${!item.is_available ? 'opacity: 0.6;' : ''}">
                <td><strong>${item.name}</strong>${item.description ? `<br><small style="color:var(--text-muted);">${item.description}</small>` : ''}</td>
                <td><span class="badge" style="background:rgba(139,92,246,0.15); color:#8b5cf6; padding:0.2rem 0.5rem; border-radius:12px; font-size:0.75rem;">${item.category || 'General'}</span></td>
                <td><strong>₹${parseFloat(item.price).toFixed(2)}</strong></td>
                <td>${item.unit || 'pcs'}</td>
                <td>
                  <button class="btn" style="padding:0.25rem 0.6rem; font-size:0.75rem; background:${item.is_available ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}; color:${item.is_available ? '#10b981' : '#ef4444'}; border:1px solid ${item.is_available ? '#10b98133' : '#ef444433'};" onclick="toggleCatalogAvailability('${item.id}', ${!item.is_available})">
                    ${item.is_available ? '✓ In Stock' : '✗ Out of Stock'}
                  </button>
                </td>
                <td style="display:flex; gap:0.25rem;">
                  <button class="btn-icon" style="color:var(--primary);" title="Edit Item" onclick='openEditCatalogModal(${JSON.stringify(item).replace(/'/g, "&#39;")})'><i data-lucide="pencil"></i></button>
                  <button class="btn-icon" style="color:var(--accent-rose);" title="Delete Item" onclick="deleteCatalogItem('${item.id}')"><i data-lucide="trash-2"></i></button>
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
    <div class="form-group">
      <label>Description (optional)</label>
      <input id="modal-cat-desc" class="form-control" placeholder="Hot filter coffee">
    </div>
  `, async () => {
    const name = document.getElementById('modal-cat-name').value;
    const price = parseFloat(document.getElementById('modal-cat-price').value);
    const category = document.getElementById('modal-cat-category').value || 'General';
    const unit = document.getElementById('modal-cat-unit').value || 'piece';
    const description = document.getElementById('modal-cat-desc').value;

    await api('/catalog', {
      method: 'POST',
      body: JSON.stringify({ name, price, category, unit, description }),
    });
    showToast('Catalog item added!');
    renderView('catalog');
  });
}

function openEditCatalogModal(item) {
  openModal('Edit Catalog Item', `
    <div class="form-group">
      <label>Item Name</label>
      <input id="modal-cat-name" class="form-control" value="${item.name}" required>
    </div>
    <div class="form-group">
      <label>Price (₹)</label>
      <input id="modal-cat-price" type="number" step="0.01" class="form-control" value="${parseFloat(item.price)}" required>
    </div>
    <div class="form-group">
      <label>Category</label>
      <input id="modal-cat-category" class="form-control" value="${item.category || 'General'}">
    </div>
    <div class="form-group">
      <label>Unit</label>
      <input id="modal-cat-unit" class="form-control" value="${item.unit || 'piece'}">
    </div>
    <div class="form-group">
      <label>Description (optional)</label>
      <input id="modal-cat-desc" class="form-control" value="${item.description || ''}">
    </div>
  `, async () => {
    const name = document.getElementById('modal-cat-name').value;
    const price = parseFloat(document.getElementById('modal-cat-price').value);
    const category = document.getElementById('modal-cat-category').value;
    const unit = document.getElementById('modal-cat-unit').value;
    const description = document.getElementById('modal-cat-desc').value;

    await api(`/catalog/${item.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ name, price, category, unit, description }),
    });
    showToast('Catalog item updated!');
    renderView('catalog');
  });
}

async function toggleCatalogAvailability(itemId, newValue) {
  try {
    await api(`/catalog/${itemId}`, {
      method: 'PATCH',
      body: JSON.stringify({ is_available: newValue }),
    });
    showToast(newValue ? 'Item marked as In Stock' : 'Item marked as Out of Stock');
    renderView('catalog');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ============================================================
// INVENTORY VIEW (NEW)
// ============================================================
let inventoryLowStockFilter = false;

async function renderInventoryView(container) {
  const items = await api(`/inventory?low_stock_only=${inventoryLowStockFilter}`);
  state.inventory = items;

  const totalItems = items.length;
  const lowStockCount = items.filter(i => i.is_low_stock).length;
  const totalStockValue = items.reduce((acc, i) => acc + parseFloat(i.current_quantity || 0), 0);

  container.innerHTML = `
    <div class="stats-grid">
      <div class="glass-panel stat-card">
        <div class="stat-icon" style="background: rgba(99, 102, 241, 0.2); color: var(--primary);">
          <i data-lucide="package"></i>
        </div>
        <div class="stat-info">
          <div class="value">${totalItems}</div>
          <div class="label">Total Items</div>
        </div>
      </div>
      <div class="glass-panel stat-card">
        <div class="stat-icon" style="background: rgba(239, 68, 68, 0.2); color: var(--accent-rose);">
          <i data-lucide="alert-triangle"></i>
        </div>
        <div class="stat-info">
          <div class="value">${lowStockCount}</div>
          <div class="label">Low Stock Alerts</div>
        </div>
      </div>
      <div class="glass-panel stat-card">
        <div class="stat-icon" style="background: rgba(16, 185, 129, 0.2); color: var(--accent-emerald);">
          <i data-lucide="bar-chart-3"></i>
        </div>
        <div class="stat-info">
          <div class="value">${totalStockValue.toFixed(1)}</div>
          <div class="label">Total Stock Units</div>
        </div>
      </div>
    </div>

    <!-- Low Stock Filter -->
    <div class="glass-panel" style="padding: 0.75rem 1.25rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.75rem;">
      <span style="font-size: 0.85rem; font-weight: 500; color: var(--text-muted);">Filter:</span>
      <button class="btn ${!inventoryLowStockFilter ? 'btn-primary' : ''}" style="padding:0.3rem 0.7rem; font-size:0.8rem;" onclick="inventoryLowStockFilter=false; renderView('inventory');">All Items</button>
      <button class="btn ${inventoryLowStockFilter ? 'btn-primary' : ''}" style="padding:0.3rem 0.7rem; font-size:0.8rem; ${inventoryLowStockFilter ? '' : lowStockCount > 0 ? 'color:var(--accent-rose);' : ''}" onclick="inventoryLowStockFilter=true; renderView('inventory');">
        🔴 Low Stock Only ${lowStockCount > 0 ? `(${lowStockCount})` : ''}
      </button>
    </div>

    <div class="glass-panel" style="padding: 1.25rem;">
      <div class="table-container">
        <table class="data-table inventory-table">
          <thead>
            <tr>
              <th>Item Name</th>
              <th>Current Qty</th>
              <th>Unit</th>
              <th>Low Threshold</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${items.length === 0 ? '<tr><td colspan="6" style="text-align:center; padding:2rem;">No inventory items found</td></tr>' : ''}
            ${items.map(item => {
              const isLow = item.is_low_stock;
              const rowStyle = isLow ? 'background: rgba(239,68,68,0.05); border-left: 3px solid var(--accent-rose);' : '';
              const threshold = item.threshold ? item.threshold.low_threshold : 5;
              return `
                <tr style="${rowStyle}">
                  <td><strong>${item.item_name}</strong></td>
                  <td style="font-weight: 600; color: ${isLow ? 'var(--accent-rose)' : 'var(--text-main)'};">${parseFloat(item.current_quantity).toFixed(1)}</td>
                  <td>${item.unit}</td>
                  <td>${threshold}</td>
                  <td>
                    ${isLow
                      ? '<span style="display:inline-block; padding:0.2rem 0.5rem; border-radius:12px; font-size:0.75rem; font-weight:600; color:#ef4444; background:rgba(239,68,68,0.15);">⚠ Low Stock</span>'
                      : '<span style="display:inline-block; padding:0.2rem 0.5rem; border-radius:12px; font-size:0.75rem; font-weight:600; color:#10b981; background:rgba(16,185,129,0.15);">✓ OK</span>'
                    }
                  </td>
                  <td style="display:flex; gap:0.25rem;">
                    <button class="btn" style="padding:0.25rem 0.5rem; font-size:0.75rem; background:rgba(16,185,129,0.15); color:#10b981;" onclick="adjustInventory('${item.id}', '${item.item_name}', 'add')">+ Add</button>
                    <button class="btn" style="padding:0.25rem 0.5rem; font-size:0.75rem; background:rgba(239,68,68,0.15); color:#ef4444;" onclick="adjustInventory('${item.id}', '${item.item_name}', 'remove')">- Use</button>
                    <button class="btn-icon" style="color:var(--primary);" title="Edit Threshold" onclick="openEditInventoryModal('${item.id}', '${item.item_name}', ${parseFloat(item.current_quantity)}, '${item.unit}', ${threshold})"><i data-lucide="settings"></i></button>
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function openCreateInventoryModal() {
  openModal('Add Inventory Item', `
    <div class="form-group">
      <label>Item Name</label>
      <input id="modal-inv-name" class="form-control" placeholder="Sugar" required>
    </div>
    <div class="form-group">
      <label>Initial Quantity</label>
      <input id="modal-inv-qty" type="number" step="0.1" class="form-control" placeholder="50" required>
    </div>
    <div class="form-group">
      <label>Unit</label>
      <input id="modal-inv-unit" class="form-control" placeholder="kg" value="units">
    </div>
    <div class="form-group">
      <label>Low Stock Threshold</label>
      <input id="modal-inv-threshold" type="number" step="0.1" class="form-control" placeholder="5" value="5">
    </div>
  `, async () => {
    const item_name = document.getElementById('modal-inv-name').value;
    const current_quantity = parseFloat(document.getElementById('modal-inv-qty').value);
    const unit = document.getElementById('modal-inv-unit').value;
    const low_threshold = parseFloat(document.getElementById('modal-inv-threshold').value);

    await api('/inventory', {
      method: 'POST',
      body: JSON.stringify({ item_name, current_quantity, unit, low_threshold }),
    });
    showToast('Inventory item added!');
    renderView('inventory');
  });
}

function adjustInventory(itemId, itemName, mode) {
  const title = mode === 'add' ? `Add Stock: ${itemName}` : `Use Stock: ${itemName}`;
  openModal(title, `
    <div class="form-group">
      <label>Quantity to ${mode === 'add' ? 'add' : 'remove'}</label>
      <input id="modal-inv-adj" type="number" step="0.1" min="0.1" class="form-control" placeholder="10" required>
    </div>
  `, async () => {
    let qty = parseFloat(document.getElementById('modal-inv-adj').value);
    if (mode === 'remove') qty = -qty;

    await api(`/inventory/${itemId}`, {
      method: 'PATCH',
      body: JSON.stringify({ quantity_change: qty }),
    });
    showToast(`Stock ${mode === 'add' ? 'added' : 'used'} successfully!`);
    renderView('inventory');
  });
}

function openEditInventoryModal(itemId, itemName, currentQty, unit, threshold) {
  openModal(`Edit: ${itemName}`, `
    <div class="form-group">
      <label>Current Quantity</label>
      <input id="modal-inv-qty" type="number" step="0.1" class="form-control" value="${currentQty}">
    </div>
    <div class="form-group">
      <label>Unit</label>
      <input id="modal-inv-unit" class="form-control" value="${unit}">
    </div>
    <div class="form-group">
      <label>Low Stock Threshold</label>
      <input id="modal-inv-threshold" type="number" step="0.1" class="form-control" value="${threshold}">
    </div>
  `, async () => {
    const current_quantity = parseFloat(document.getElementById('modal-inv-qty').value);
    const unitVal = document.getElementById('modal-inv-unit').value;
    const low_threshold = parseFloat(document.getElementById('modal-inv-threshold').value);

    await api(`/inventory/${itemId}`, {
      method: 'PATCH',
      body: JSON.stringify({ current_quantity, unit: unitVal, low_threshold }),
    });
    showToast('Inventory item updated!');
    renderView('inventory');
  });
}

// ============================================================
// CUSTOMERS VIEW
// ============================================================
async function renderCustomersView(container) {
  const customers = await api('/customers');
  state.customers = customers;

  container.innerHTML = `
    <div class="glass-panel" style="padding: 1.25rem;">
      <div class="table-container">
        <table class="data-table customers-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Phone Number</th>
              <th>Created At</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${customers.length === 0 ? '<tr><td colspan="4" style="text-align:center; padding:2rem;">No customers found</td></tr>' : ''}
            ${customers.map((c) => `
              <tr>
                <td><strong>${c.name || 'Anonymous'}</strong></td>
                <td>${c.phone_number}</td>
                <td>${new Date(c.created_at).toLocaleDateString()}</td>
                <td>
                  <button class="btn-icon" style="color:var(--accent-rose);" title="Delete Customer" onclick="deleteCustomer('${c.id}')"><i data-lucide="trash-2"></i></button>
                </td>
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

// ============================================================
// RESERVATIONS VIEW
// ============================================================
let reservationViewMode = 'list';
let reservationDateFilter = new Date().toISOString().slice(0, 10);

async function renderReservationsView(container) {
  const reservations = await api(`/reservations?date=${reservationDateFilter}`);
  const settings = await api('/business/settings').catch(() => ({ table_count: 10, reservation_slot_duration: 90, opening_time: '10:00', closing_time: '22:00' }));
  state.reservations = reservations;

  let availabilityData = null;
  try {
    availabilityData = await api(`/reservations/availability?date=${reservationDateFilter}`);
  } catch (e) {}

  container.innerHTML = `
    <!-- Settings Panel -->
    <div class="glass-panel" style="padding: 1.25rem; margin-bottom: 1.5rem;">
      <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
        <div>
          <h4 style="margin: 0 0 0.25rem 0; font-size: 1.1rem; color: var(--text-main);">Shop Table & Reservation Settings</h4>
          <p style="margin: 0; font-size: 0.875rem; color: var(--text-muted);">Configure capacity, slot duration, and operating hours</p>
        </div>
        <div style="display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;">
          <div style="display: flex; align-items: center; gap: 0.35rem;">
            <label style="font-size: 0.8rem; font-weight: 500; color: var(--text-main);">Tables:</label>
            <input id="shop-table-count" type="number" min="1" max="500" class="form-control" style="width: 70px; text-align: center;" value="${settings.table_count || 10}">
          </div>
          <div style="display: flex; align-items: center; gap: 0.35rem;">
            <label style="font-size: 0.8rem; font-weight: 500; color: var(--text-main);">Slot (min):</label>
            <input id="shop-slot-duration" type="number" min="15" max="300" class="form-control" style="width: 70px; text-align: center;" value="${settings.reservation_slot_duration || 90}">
          </div>
          <div style="display: flex; align-items: center; gap: 0.35rem;">
            <label style="font-size: 0.8rem; font-weight: 500; color: var(--text-main);">Open:</label>
            <input id="shop-opening-time" type="time" class="form-control" style="width: 100px;" value="${settings.opening_time || '10:00'}">
          </div>
          <div style="display: flex; align-items: center; gap: 0.35rem;">
            <label style="font-size: 0.8rem; font-weight: 500; color: var(--text-main);">Close:</label>
            <input id="shop-closing-time" type="time" class="form-control" style="width: 100px;" value="${settings.closing_time || '22:00'}">
          </div>
          <button class="btn btn-primary" style="padding: 0.4rem 0.8rem; font-size: 0.875rem;" onclick="updateShopReservationSettings()"><i data-lucide="save"></i> Save</button>
        </div>
      </div>
    </div>

    <!-- View Controls -->
    <div class="glass-panel" style="padding: 1rem; margin-bottom: 1.5rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.75rem;">
      <div style="display: flex; align-items: center; gap: 0.5rem;">
        <label style="font-size: 0.875rem; font-weight: 500; color: var(--text-main);">Date:</label>
        <input id="res-date-filter" type="date" class="form-control" style="width: 165px;" value="${reservationDateFilter}" onchange="reservationDateFilter=this.value; renderView('reservations');">
      </div>
      <div style="display: flex; gap: 0.5rem;">
        <button class="btn ${reservationViewMode === 'list' ? 'btn-primary' : ''}" style="padding: 0.35rem 0.7rem; font-size: 0.8rem;" onclick="reservationViewMode='list'; renderView('reservations');"><i data-lucide="list"></i> List</button>
        <button class="btn ${reservationViewMode === 'grid' ? 'btn-primary' : ''}" style="padding: 0.35rem 0.7rem; font-size: 0.8rem;" onclick="reservationViewMode='grid'; renderView('reservations');"><i data-lucide="grid-3x3"></i> Table Grid</button>
        <button class="btn ${reservationViewMode === 'timeline' ? 'btn-primary' : ''}" style="padding: 0.35rem 0.7rem; font-size: 0.8rem;" onclick="reservationViewMode='timeline'; renderView('reservations');"><i data-lucide="bar-chart-3"></i> Timeline</button>
      </div>
    </div>

    <div id="reservation-view-content"></div>
  `;

  const viewContent = document.getElementById('reservation-view-content');
  if (reservationViewMode === 'grid') {
    renderTableGridView(viewContent, availabilityData, settings);
  } else if (reservationViewMode === 'timeline') {
    renderTimelineView(viewContent, availabilityData, settings);
  } else {
    renderReservationListView(viewContent, reservations);
  }
}

function renderReservationListView(container, reservations) {
  container.innerHTML = `
    <div class="glass-panel" style="padding: 1.25rem;">
      <div class="table-container">
        <table class="data-table reservations-table">
          <thead>
            <tr>
              <th>Customer</th>
              <th>Party Size</th>
              <th>Table</th>
              <th>Reserved Date/Time</th>
              <th>Duration</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${reservations.length === 0 ? '<tr><td colspan="7" style="text-align:center; padding:2rem;">No reservations found</td></tr>' : ''}
            ${reservations.map((r) => `
              <tr>
                <td><strong>${r.customer_name || 'Guest'}</strong></td>
                <td>${r.party_size} People</td>
                <td><span class="badge badge-confirmed">${r.table_or_slot || 'Unassigned'}</span></td>
                <td>${new Date(r.reserved_at).toLocaleString()}</td>
                <td>${r.duration_minutes} min</td>
                <td>${statusBadge(r.status)}</td>
                <td>
                  <button class="btn-icon" style="color:var(--accent-rose);" title="Delete Reservation" onclick="deleteReservation('${r.id}')"><i data-lucide="trash-2"></i></button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderTableGridView(container, availabilityData, settings) {
  if (!availabilityData) {
    container.innerHTML = '<div class="glass-panel" style="padding: 2rem; text-align: center; color: var(--text-muted);">Loading availability data...</div>';
    return;
  }
  const grid = availabilityData.table_grid || [];
  container.innerHTML = `
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 1rem;">
      ${grid.map(t => {
        const isReserved = t.status === 'reserved';
        const borderColor = isReserved ? 'rgba(239, 68, 68, 0.4)' : 'rgba(16, 185, 129, 0.4)';
        const bgColor = isReserved ? 'rgba(239, 68, 68, 0.05)' : 'rgba(16, 185, 129, 0.05)';
        return `
          <div class="glass-panel" style="padding: 1.25rem; border: 1px solid ${borderColor}; background: ${bgColor};">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
              <h4 style="margin: 0; font-size: 1.1rem; font-weight: 600;">${t.table_name}</h4>
              <span style="padding:0.2rem 0.5rem; border-radius:12px; font-size:0.75rem; font-weight:600; color:${isReserved ? '#ef4444' : '#10b981'}; background:${isReserved ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)'};">${isReserved ? 'Occupied' : 'Available'}</span>
            </div>
            ${t.bookings.length > 0 ? `
              <div style="margin-top: 0.75rem; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 0.6rem;">
                ${t.bookings.map(b => `
                  <div style="display: flex; align-items: center; justify-content: space-between; font-size: 0.825rem; padding: 0.4rem 0.6rem; background: rgba(0,0,0,0.2); border-radius: 6px; margin-bottom: 0.4rem;">
                    <div>
                      <strong style="display: block;">${b.customer}</strong>
                      <span style="font-size: 0.75rem; color: var(--text-subtle);">${b.party_size} guests · ${b.duration}m</span>
                    </div>
                    <span style="font-weight: 600; color: var(--accent-indigo); font-size: 0.8rem;">${b.time}</span>
                  </div>
                `).join('')}
              </div>
            ` : `<p style="font-size: 0.8rem; color: var(--text-subtle); margin: 0.5rem 0 0;">Free all day</p>`}
          </div>
        `;
      }).join('')}
    </div>
  `;
}

function renderTimelineView(container, availabilityData, settings) {
  if (!availabilityData) {
    container.innerHTML = '<div class="glass-panel" style="padding: 2rem; text-align: center; color: var(--text-muted);">Loading timeline data...</div>';
    return;
  }
  const matrix = availabilityData.hourly_matrix || [];
  const totalTables = availabilityData.total_tables || 10;
  container.innerHTML = `
    <div class="glass-panel" style="padding: 1.25rem;">
      <h4 style="margin: 0 0 1rem; font-size: 1.1rem;">Hourly Table Occupancy — ${availabilityData.date}</h4>
      <div style="display: flex; flex-direction: column; gap: 0.5rem;">
        ${matrix.map(slot => {
          const pct = totalTables > 0 ? ((slot.occupied / totalTables) * 100).toFixed(0) : 0;
          const isFull = slot.available === 0;
          const barColor = isFull ? 'var(--accent-rose)' : pct > 60 ? 'var(--accent-amber)' : 'var(--accent-emerald)';
          return `
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              <div style="width: 80px; font-size: 0.85rem; font-weight: 500; flex-shrink: 0;">${slot.hour}</div>
              <div style="flex: 1; background: var(--card-bg); border-radius: 6px; height: 28px; overflow: hidden; position: relative; border: 1px solid var(--border);">
                <div style="height: 100%; width: ${pct}%; background: ${barColor}; border-radius: 6px; transition: width 0.5s ease;"></div>
                <span style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%); font-size: 0.75rem; font-weight: 600;">${slot.occupied}/${totalTables} ${isFull ? '🔴 FULL' : ''}</span>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    </div>
  `;
}

async function updateShopReservationSettings() {
  const table_count = parseInt(document.getElementById('shop-table-count').value) || 10;
  const reservation_slot_duration = parseInt(document.getElementById('shop-slot-duration').value) || 90;
  const opening_time = document.getElementById('shop-opening-time').value || '10:00';
  const closing_time = document.getElementById('shop-closing-time').value || '22:00';

  await api('/business/settings', {
    method: 'PUT',
    body: JSON.stringify({ table_count, reservation_slot_duration, opening_time, closing_time }),
  });
  showToast('Reservation settings saved!');
  renderView('reservations');
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

    try {
      await api('/reservations', {
        method: 'POST',
        body: JSON.stringify({ customer_name, customer_phone, party_size, reserved_at }),
      });
      showToast('Reservation created! Table auto-assigned.');
      renderView('reservations');
    } catch (err) {
      showToast(err.message || 'Failed to create reservation — slot may be full', 'error');
    }
  });
}

// ============================================================
// CONVERSATIONS VIEW
// ============================================================
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

      <div class="glass-panel chat-main">
        ${selectedThread ? `
          <div class="chat-header">
            <div>
              <h3 style="font-size: 1.15rem;">${selectedThread.customer_name}</h3>
              <span style="font-size: 0.8rem; color: var(--text-muted);">${selectedThread.phone_number}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              <span class="badge badge-channel">WhatsApp AI Chat</span>
              <button class="btn" style="padding: 0.35rem 0.7rem; font-size: 0.8rem; background: rgba(239, 68, 68, 0.1); color: var(--accent-rose); border: 1px solid rgba(239, 68, 68, 0.2);" onclick="deleteConversation('${selectedThread.phone_number}')">
                <i data-lucide="trash-2" style="width: 14px; height: 14px; margin-right: 4px; display: inline-block; vertical-align: middle;"></i> Delete Thread
              </button>
            </div>
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

  const msgContainer = document.getElementById('chat-messages-container');
  if (msgContainer) {
    msgContainer.scrollTop = msgContainer.scrollHeight;
  }
}

function selectChatThread(phone) {
  activeThreadPhone = phone;
  renderView('conversations');
}

async function deleteConversation(phone) {
  if (!confirm('Are you sure you want to delete this conversation thread?')) return;
  try {
    await api(`/conversations/${phone}`, { method: 'DELETE' });
    showToast('Conversation thread deleted!');
    activeThreadPhone = null;
    renderView('conversations');
  } catch (err) {
    showToast('Failed to delete conversation: ' + err.message, 'error');
  }
}

// ============================================================
// ANALYTICS VIEW — Chart.js Powered
// ============================================================
let chartInstances = {};

function destroyCharts() {
  Object.values(chartInstances).forEach(c => { if (c && c.destroy) c.destroy(); });
  chartInstances = {};
}

async function renderAnalyticsView(container) {
  destroyCharts();

  const [analytics, trends] = await Promise.all([
    api('/analytics/summary'),
    api('/analytics/trends').catch(() => ({ daily_stats: [], top_items: [], status_breakdown: {} })),
  ]);

  const rev = parseFloat(analytics.total_revenue || 0);
  const totalOrders = analytics.total_orders || 0;
  const customers = analytics.total_customers || 0;
  const totalReservations = analytics.total_reservations || 0;
  const lowStock = analytics.low_stock_items_count || 0;

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
          <div class="label">Reservations</div>
        </div>
      </div>
    </div>

    <!-- Charts Row 1 -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 1.5rem; margin-top: 1rem;">
      <div class="glass-panel chart-card">
        <h3>📈 Revenue Trend (7 Days)</h3>
        <div style="position: relative; height: 250px;"><canvas id="chart-revenue"></canvas></div>
      </div>
      <div class="glass-panel chart-card">
        <h3>📊 Orders per Day (7 Days)</h3>
        <div style="position: relative; height: 250px;"><canvas id="chart-orders-daily"></canvas></div>
      </div>
    </div>

    <!-- Charts Row 2 -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 1.5rem; margin-top: 1.5rem;">
      <div class="glass-panel chart-card">
        <h3>🏆 Top Selling Items</h3>
        <div style="position: relative; height: 250px;"><canvas id="chart-top-items"></canvas></div>
      </div>
      <div class="glass-panel chart-card">
        <h3>🍩 Order Status Breakdown</h3>
        <div style="position: relative; height: 250px; display:flex; justify-content:center;"><canvas id="chart-status" style="max-width:280px;"></canvas></div>
      </div>
    </div>

    <!-- Operations Health -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 1.5rem; margin-top: 1.5rem;">
      <div class="glass-panel chart-card">
        <h3>🏥 Operations Health</h3>
        <div style="display:flex; align-items:center; justify-content:space-between; padding: 0.75rem 0; border-bottom:1px solid var(--border-glass);">
          <span style="color:var(--text-muted);">Low Stock Alerts</span>
          <span style="padding:0.2rem 0.5rem; border-radius:12px; font-size:0.8rem; font-weight:600; color:${lowStock > 0 ? '#ef4444' : '#10b981'}; background:${lowStock > 0 ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)'};">${lowStock} items low</span>
        </div>
        <div style="display:flex; align-items:center; justify-content:space-between; padding: 0.75rem 0;">
          <span style="color:var(--text-muted);">AI Communication Channel</span>
          <span class="badge badge-channel">Twilio WhatsApp</span>
        </div>
      </div>
    </div>
  `;

  // Render Chart.js charts
  const chartDefaults = {
    color: '#94a3b8',
    borderColor: 'rgba(255,255,255,0.08)',
  };

  // Revenue Trend Line Chart
  const revCtx = document.getElementById('chart-revenue');
  if (revCtx && trends.daily_stats.length > 0) {
    chartInstances.revenue = new Chart(revCtx, {
      type: 'line',
      data: {
        labels: trends.daily_stats.map(d => d.label),
        datasets: [{
          label: 'Revenue (₹)',
          data: trends.daily_stats.map(d => d.revenue),
          borderColor: '#10b981',
          backgroundColor: 'rgba(16,185,129,0.1)',
          fill: true,
          tension: 0.4,
          pointBackgroundColor: '#10b981',
          pointRadius: 5,
          pointHoverRadius: 7,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: chartDefaults.color }, grid: { color: chartDefaults.borderColor } },
          y: { ticks: { color: chartDefaults.color, callback: v => '₹' + v }, grid: { color: chartDefaults.borderColor }, beginAtZero: true },
        },
      },
    });
  }

  // Orders Bar Chart
  const ordCtx = document.getElementById('chart-orders-daily');
  if (ordCtx && trends.daily_stats.length > 0) {
    chartInstances.ordersDaily = new Chart(ordCtx, {
      type: 'bar',
      data: {
        labels: trends.daily_stats.map(d => d.label),
        datasets: [{
          label: 'Orders',
          data: trends.daily_stats.map(d => d.orders),
          backgroundColor: 'rgba(99,102,241,0.6)',
          borderColor: '#6366f1',
          borderWidth: 1,
          borderRadius: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: chartDefaults.color }, grid: { color: chartDefaults.borderColor } },
          y: { ticks: { color: chartDefaults.color, stepSize: 1 }, grid: { color: chartDefaults.borderColor }, beginAtZero: true },
        },
      },
    });
  }

  // Top Items Horizontal Bar
  const topCtx = document.getElementById('chart-top-items');
  if (topCtx && trends.top_items.length > 0) {
    const colors = ['#6366f1', '#8b5cf6', '#f59e0b', '#10b981', '#06b6d4'];
    chartInstances.topItems = new Chart(topCtx, {
      type: 'bar',
      data: {
        labels: trends.top_items.map(i => i.item_name),
        datasets: [{
          label: 'Qty Sold',
          data: trends.top_items.map(i => i.total_quantity),
          backgroundColor: trends.top_items.map((_, idx) => colors[idx % colors.length] + '99'),
          borderColor: trends.top_items.map((_, idx) => colors[idx % colors.length]),
          borderWidth: 1,
          borderRadius: 6,
        }],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: chartDefaults.color, stepSize: 1 }, grid: { color: chartDefaults.borderColor }, beginAtZero: true },
          y: { ticks: { color: chartDefaults.color }, grid: { display: false } },
        },
      },
    });
  }

  // Status Donut
  const statusCtx = document.getElementById('chart-status');
  if (statusCtx && Object.keys(trends.status_breakdown).length > 0) {
    const statusColors = {
      pending: '#f59e0b', pending_confirmation: '#3b82f6', confirmed: '#10b981',
      in_preparation: '#f97316', out_for_delivery: '#8b5cf6', delivered: '#22c55e',
      completed: '#06b6d4', cancelled: '#ef4444', draft: '#6b7280', ready: '#06b6d4',
    };
    const labels = Object.keys(trends.status_breakdown);
    const data = Object.values(trends.status_breakdown);
    chartInstances.status = new Chart(statusCtx, {
      type: 'doughnut',
      data: {
        labels: labels.map(l => (STATUS_CONFIG[l]?.label || l)),
        datasets: [{
          data,
          backgroundColor: labels.map(l => (statusColors[l] || '#6b7280') + 'cc'),
          borderColor: labels.map(l => statusColors[l] || '#6b7280'),
          borderWidth: 2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right', labels: { color: chartDefaults.color, padding: 12, usePointStyle: true } },
        },
      },
    });
  }
}

// ============================================================
// MODAL HELPER
// ============================================================
function openModal(title, contentHtml, onSubmit, submitText = 'Save Changes', submitBtnClass = 'btn-primary') {
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
          <button type="submit" class="btn ${submitBtnClass}">${submitText}</button>
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

// ============================================================
// DELETE HELPERS
// ============================================================
function showDeleteConfirmation(itemName, onConfirmDelete) {
  openModal(
    'Confirm Deletion',
    `
    <div style="text-align: center; padding: 0.5rem 0 1rem;">
      <div style="width: 52px; height: 52px; background: #fee2e2; color: var(--accent-rose); border-radius: var(--radius-full); display: inline-flex; align-items: center; justify-content: center; margin-bottom: 1rem; border: 1px solid #fecaca;">
        <i data-lucide="trash-2" style="width: 24px; height: 24px;"></i>
      </div>
      <h3 style="font-size: 1.15rem; font-weight: 700; margin-bottom: 0.5rem; color: var(--text-main);">Delete ${itemName}?</h3>
      <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 0.5rem;">Are you sure you want to delete this ${itemName.toLowerCase()}? This action cannot be undone.</p>
    </div>
    `,
    async () => {
      await onConfirmDelete();
    },
    'Delete Permanently',
    'btn-danger'
  );
}

async function deleteOrder(id) {
  showDeleteConfirmation('Order', async () => {
    try {
      await api(`/orders/${id}`, { method: 'DELETE' });
      showToast('Order deleted successfully!');
      renderView('orders');
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

async function deleteCatalogItem(id) {
  showDeleteConfirmation('Catalog Item', async () => {
    try {
      await api(`/catalog/${id}`, { method: 'DELETE' });
      showToast('Catalog item deleted successfully!');
      renderView('catalog');
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

async function deleteCustomer(id) {
  showDeleteConfirmation('Customer', async () => {
    try {
      await api(`/customers/${id}`, { method: 'DELETE' });
      showToast('Customer deleted successfully!');
      renderView('customers');
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

async function deleteReservation(id) {
  showDeleteConfirmation('Reservation', async () => {
    try {
      await api(`/reservations/${id}`, { method: 'DELETE' });
      showToast('Reservation deleted successfully!');
      renderView('reservations');
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

// ============================================================
// GLOBAL EXPORTS
// ============================================================
window.openCreateOrderModal = openCreateOrderModal;
window.openCreateCatalogModal = openCreateCatalogModal;
window.openEditCatalogModal = openEditCatalogModal;
window.toggleCatalogAvailability = toggleCatalogAvailability;
window.openCreateCustomerModal = openCreateCustomerModal;
window.openCreateReservationModal = openCreateReservationModal;
window.openCreateInventoryModal = openCreateInventoryModal;
window.adjustInventory = adjustInventory;
window.openEditInventoryModal = openEditInventoryModal;
window.updateOrderStatus = updateOrderStatus;
window.deleteOrder = deleteOrder;
window.deleteCatalogItem = deleteCatalogItem;
window.deleteCustomer = deleteCustomer;
window.deleteReservation = deleteReservation;
window.updateShopReservationSettings = updateShopReservationSettings;
window.selectChatThread = selectChatThread;
window.closeModal = closeModal;
window.logout = logout;
window.confirmLogout = confirmLogout;

// Start background auto-refresh every 5 seconds
setInterval(async () => {
  if (state.token && !document.getElementById('modal-root')?.classList.contains('active')) {
    const mainView = document.getElementById('main-view');
    if (mainView && state.currentRoute) {
      try {
        if (state.currentRoute === 'orders') {
          await renderOrdersView(mainView);
          lucide.createIcons();
        } else if (state.currentRoute === 'reservations') {
          await renderReservationsView(mainView);
          lucide.createIcons();
        }
      } catch (err) {
        console.error('Auto-refresh failed:', err);
      }
    }
  }
}, 5000);

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', initAuth);
