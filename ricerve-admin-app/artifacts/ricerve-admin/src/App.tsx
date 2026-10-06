import { type FormEvent, type ReactNode, useEffect, useState } from 'react';
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import { ErrorBoundary } from '@/components/error-boundary';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import {
  setBaseUrl,
  useGetAdminAuth,
  useGetAdminDashboard,
  useGetAdminProducts,
  useCreateAdminProduct,
  useUpdateAdminProduct,
  useDeleteAdminProduct,
  useGetAdminGroups,
  useCreateAdminGroup,
  useUpdateAdminGroup,
  useDeleteAdminGroup,
  useGetAdminUsers,
  useAdjustAdminUserBalance,
  useGetAdminPurchases,
  useGetAdminPromoCodes,
  useCreateAdminPromoCode,
  useDeleteAdminPromoCode,
  useGetAdminSettings,
  useUpdateAdminSettings,
  getGetAdminProductsQueryKey,
  getGetAdminGroupsQueryKey,
  getGetAdminUsersQueryKey,
  getGetAdminPurchasesQueryKey,
  getGetAdminPromoCodesQueryKey,
  getGetAdminSettingsQueryKey,
  getGetAdminDashboardQueryKey,
  type ShopProduct,
  type ProductGroup,
  type ShopCustomer,
} from '@workspace/api-client-react';
import {
  Activity, ArrowUpRight, BadgePercent, Box, Check, ChevronRight,
  CircleHelp, Command, ExternalLink, FolderKanban, LayoutDashboard, Link2,
  LoaderCircle, LogOut, Menu, Package, Plus, Search, Settings2, ShieldAlert,
  ShoppingBag, SlidersHorizontal, Sparkles, Users, X, RefreshCw, Trash2, Pencil,
} from 'lucide-react';
import { Link, Route, Switch, useLocation, Router as WouterRouter } from 'wouter';
import NotFound from '@/pages/not-found';

// API backend for the Ricerve admin panel.
setBaseUrl('https://yyjytu.infrlo.com');

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 15_000, retry: 1, refetchOnWindowFocus: false } },
});

const navItems = [
  { href: '/', label: 'Overview', icon: LayoutDashboard },
  { href: '/products', label: 'Products', icon: Package },
  { href: '/customers', label: 'Customers', icon: Users },
  { href: '/orders', label: 'Orders', icon: ShoppingBag },
  { href: '/promocodes', label: 'Promo codes', icon: BadgePercent },
  { href: '/settings', label: 'Settings', icon: Settings2 },
];

function currency(value: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(value || 0);
}
function dateLabel(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' }).format(date);
}
function personName(user: Pick<ShopCustomer, 'firstName' | 'username' | 'userId'> | { firstName?: string | null; username?: string | null; userId?: number }) {
  return user.firstName || (user.username ? `@${user.username}` : `Telegram user ${user.userId ?? ''}`);
}

function Button({ children, onClick, variant = 'primary', type = 'button', disabled = false, testid, className = '' }: {
  children: ReactNode; onClick?: () => void; variant?: 'primary' | 'quiet' | 'danger' | 'outline'; type?: 'button' | 'submit'; disabled?: boolean; testid: string; className?: string;
}) {
  return <button type={type} onClick={onClick} disabled={disabled} data-testid={testid} className={`btn btn-${variant} ${className}`}>{children}</button>;
}
function PageTitle({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-title fade-in"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action && <div className="title-action">{action}</div>}</div>;
}
function Surface({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`surface ${className}`}>{children}</section>;
}
function LoadingBlock({ rows = 4 }: { rows?: number }) {
  return <div className="loading-block" aria-label="Loading"><span className="skeleton" style={{ width: '34%', height: 20 }} />{Array.from({ length: rows }, (_, i) => <span className="skeleton" key={i} style={{ width: `${96 - (i % 3) * 11}%`, height: 42 }} />)}</div>;
}
function QueryError({ message, retry }: { message: string; retry: () => void }) {
  return <div className="state-card error-state" data-testid="status-load-error"><span className="state-icon"><RefreshCw size={19} /></span><strong>Could not load this view</strong><p>{message}</p><Button variant="outline" testid="button-retry" onClick={retry}>Try again</Button></div>;
}
function EmptyState({ icon: Icon = Box, title, detail }: { icon?: typeof Box; title: string; detail: string }) {
  return <div className="state-card"><span className="state-icon"><Icon size={21} /></span><strong>{title}</strong><p>{detail}</p></div>;
}
function Modal({ title, description, onClose, children, testid }: { title: string; description?: string; onClose: () => void; children: ReactNode; testid: string }) {
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" data-testid={testid}>
      <div className="modal-heading"><div><h2 id="modal-title">{title}</h2>{description && <p>{description}</p>}</div><button className="icon-button" onClick={onClose} aria-label="Close dialog" data-testid="button-close-modal"><X size={18} /></button></div>
      {children}
    </section>
  </div>;
}
function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return <label className="field"><span>{label}</span>{children}{hint && <small>{hint}</small>}</label>;
}
function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  return <div className="form-error" role="alert">{error instanceof Error ? error.message : 'The change could not be saved. Try again.'}</div>;
}

function AuthGate() {
  const auth = useGetAdminAuth();
  const isTelegram = Boolean((window as Window & { Telegram?: { WebApp?: { initData?: string } } }).Telegram?.WebApp?.initData);
  if (auth.isLoading) return <div className="auth-loading"><span className="brand-mark">R</span><div className="skeleton" style={{ width: 165, height: 14 }} /><div className="skeleton" style={{ width: 250, height: 9 }} /></div>;
  if (auth.isError || !auth.data?.authorized) {
    return <main className="entry-screen grain"><div className="entry-card fade-in">
      <div className="entry-brand"><span className="brand-mark">R</span><span>RICERVE <i>CONTROL</i></span></div>
      <div className="entry-orbit"><ShieldAlert size={26} /></div>
      <div className="eyebrow">PRIVATE SHOP CONSOLE</div>
      <h1>{isTelegram ? 'Access is restricted.' : 'Open inside Telegram.'}</h1>
      <p>{isTelegram ? 'This Telegram account is not authorized to manage the Ricerve shop.' : 'The admin console uses your Telegram Mini App session. Open it from the Ricerve bot to continue.'}</p>
      <div className="entry-note"><span className="status-dot" />{auth.isError ? 'Waiting for a valid Telegram session' : 'Telegram authorization required'}</div>
      <Button variant="outline" onClick={() => void auth.refetch()} testid="button-auth-retry"><RefreshCw size={15} /> Check access again</Button>
      <div className="entry-foot"><span>SECURE ADMIN</span><span>TELEGRAM MINI APP</span></div>
    </div></main>;
  }
  return <AdminShell username={auth.data.username || 'Shop owner'} />;
}

function AdminShell({ username }: { username: string }) {
  const [location] = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const current = navItems.find((item) => item.href === location);
  return <div className="app-shell grain">
    <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
      <div className="brand-lockup"><span className="brand-mark">R</span><div><strong>RICERVE</strong><small>SHOP CONTROL</small></div></div>
      <div className="sidebar-label">WORKSPACE</div>
      <nav className="nav-list">
        {navItems.map((item) => {
          const Icon = item.icon;
          return <Link key={item.href} href={item.href} onClick={() => setMobileOpen(false)} className={`nav-link ${location === item.href ? 'nav-active' : ''}`} data-testid={`link-nav-${item.label.toLowerCase().replaceAll(' ', '-')}`}><Icon size={17} strokeWidth={1.8} /><span>{item.label}</span>{location === item.href && <span className="nav-active-mark" />}</Link>;
        })}
      </nav>
      <div className="sidebar-bottom">
        <div className="mini-status"><span className="status-dot" /><div><strong>Shop connected</strong><small>Telegram storefront</small></div></div>
        <div className="owner-row"><div className="owner-avatar">{username.slice(0, 1).toUpperCase()}</div><div className="owner-copy"><strong>{username}</strong><small>Owner access</small></div><LogOut size={15} className="owner-out" /></div>
      </div>
    </aside>
    <div className="main-column">
      <header className="topbar">
        <button className="mobile-menu icon-button" onClick={() => setMobileOpen((v) => !v)} aria-label="Toggle navigation" data-testid="button-mobile-menu"><Menu size={19} /></button>
        <div className="crumb"><span>Ricerve</span><ChevronRight size={14} /><strong>{current?.label || 'Overview'}</strong></div>
        <div className="top-meta"><span className="live-pill"><span /> LIVE SHOP</span><span className="top-date">{new Intl.DateTimeFormat('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).format(new Date())}</span></div>
      </header>
      <main className="page-content">
        <Switch>
          <Route path="/" component={DashboardPage} />
          <Route path="/products" component={ProductsPage} />
          <Route path="/customers" component={CustomersPage} />
          <Route path="/orders" component={OrdersPage} />
          <Route path="/promocodes" component={PromoPage} />
          <Route path="/settings" component={SettingsPage} />
          <Route component={NotFound} />
        </Switch>
        <footer className="app-footer"><span>RICERVE CONTROL ROOM</span><span>Live data from Telegram shop <span className="footer-dot" /></span></footer>
      </main>
    </div>
  </div>;
}

function DashboardPage() {
  const dashboard = useGetAdminDashboard();
  if (dashboard.isLoading) return <><PageTitle eyebrow="SHOP PULSE / 01" title="Overview" description="A live read on what is happening in your shop." /><LoadingBlock rows={6} /></>;
  if (dashboard.isError || !dashboard.data) return <><PageTitle eyebrow="SHOP PULSE / 01" title="Overview" description="A live read on what is happening in your shop." /><QueryError message="The shop summary is temporarily unavailable." retry={() => void dashboard.refetch()} /></>;
  const d = dashboard.data;
  const stats = [
    { label: 'Gross revenue', value: currency(d.grossRevenue), icon: ArrowUpRight, note: 'All completed purchases', feature: true },
    { label: 'Total purchases', value: d.totalPurchases.toLocaleString(), icon: ShoppingBag, note: `${d.pendingPayments} pending payments` },
    { label: 'Shop customers', value: d.totalUsers.toLocaleString(), icon: Users, note: `${d.activeUsers.toLocaleString()} active customers` },
    { label: 'Live products', value: d.totalProducts.toLocaleString(), icon: Package, note: 'Available in Telegram' },
  ];
  return <div className="fade-in">
    <PageTitle eyebrow="SHOP PULSE / 01" title="Overview" description="A live read on what is happening in your shop." action={<span className="synced-note"><span className="status-dot" />Synced just now</span>} />
    <div className="stats-grid">
      {stats.map((stat, index) => { const Icon = stat.icon; return <Surface key={stat.label} className={`stat-card ${stat.feature ? 'stat-feature' : ''}`}><div className="stat-top"><span>{stat.label}</span><Icon size={17} /></div><strong data-testid={`metric-${stat.label.toLowerCase().replaceAll(' ', '-')}`}>{stat.value}</strong><small>{stat.note}</small><div className={`stat-index mono ${index === 0 ? 'stat-index-feature' : ''}`}>0{index + 1}</div></Surface>; })}
    </div>
    <div className="dashboard-lower">
      <Surface className="recent-surface"><div className="surface-heading"><div><div className="eyebrow">TRANSACTION STREAM</div><h2>Recent purchases</h2></div><Link href="/orders" className="text-link" data-testid="link-view-all-orders">All purchases <ChevronRight size={15} /></Link></div>
        {d.recentPurchases?.length ? <div className="table-scroll"><table><thead><tr><th>Customer</th><th>Product</th><th>Amount</th><th>Purchased</th></tr></thead><tbody>{d.recentPurchases.map((purchase) => <tr key={purchase.id} data-testid={`row-purchase-${purchase.id}`}><td><div className="person-cell"><span className="table-avatar">{(purchase.firstName || purchase.username || 'R').slice(0, 1).toUpperCase()}</span><div><strong>{personName(purchase)}</strong><small>Telegram ID {purchase.userId}</small></div></div></td><td>{purchase.productName}</td><td className="mono amount-cell">{currency(purchase.price)}</td><td className="muted-cell">{dateLabel(purchase.purchasedAt)}</td></tr>)}</tbody></table></div> : <EmptyState icon={ShoppingBag} title="No purchases yet" detail="Completed purchases from your Telegram shop will appear here." />}
      </Surface>
      <Surface className="pulse-card"><div className="pulse-top"><span className="pulse-icon"><Activity size={18} /></span><span className="eyebrow">SHOP HEALTH</span></div><div className="pulse-title">Everything in<br />one rhythm.</div><p>Products, customers and payments are flowing through your Telegram storefront.</p><div className="pulse-divider" /><div className="pulse-foot"><span>ACTIVE CUSTOMERS</span><strong>{d.activeUsers.toLocaleString()}</strong></div></Surface>
    </div>
    <div className="quick-row"><span className="eyebrow">DIRECT ACCESS</span>{navItems.slice(1, 4).map((item) => { const Icon = item.icon; return <Link href={item.href} className="quick-link" key={item.href} data-testid={`link-quick-${item.label.toLowerCase()}`}><Icon size={15} />{item.label}<ArrowUpRight size={14} /></Link>; })}</div>
  </div>;
}

function ProductsPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [groupFilter, setGroupFilter] = useState('all');
  const [editing, setEditing] = useState<ShopProduct | null>(null);
  const [productModal, setProductModal] = useState(false);
  const [groupModal, setGroupModal] = useState(false);
  const [editingGroup, setEditingGroup] = useState<ProductGroup | null>(null);
  const products = useGetAdminProducts({ search: search || undefined, groupId: groupFilter === 'all' ? undefined : Number(groupFilter) });
  const groups = useGetAdminGroups();
  const createProduct = useCreateAdminProduct();
  const updateProduct = useUpdateAdminProduct();
  const deleteProduct = useDeleteAdminProduct();
  const createGroup = useCreateAdminGroup();
  const updateGroup = useUpdateAdminGroup();
  const deleteGroup = useDeleteAdminGroup();
  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: getGetAdminProductsQueryKey() });
    void qc.invalidateQueries({ queryKey: getGetAdminGroupsQueryKey() });
    void qc.invalidateQueries({ queryKey: getGetAdminDashboardQueryKey() });
  };
  const saveProduct = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const data = { name: String(form.get('name')).trim(), price: Number(form.get('price')), content: String(form.get('content')), contentType: String(form.get('contentType')), groupId: form.get('groupId') ? Number(form.get('groupId')) : null, photoId: String(form.get('photoId') || '').trim() || null };
    if (editing) updateProduct.mutate({ productId: editing.id, data }, { onSuccess: () => { invalidate(); setEditing(null); setProductModal(false); } });
    else createProduct.mutate({ data }, { onSuccess: () => { invalidate(); setProductModal(false); } });
  };
  const saveGroup = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const data = { name: String(form.get('name')).trim(), parentId: form.get('parentId') ? Number(form.get('parentId')) : null };
    if (editingGroup) updateGroup.mutate({ groupId: editingGroup.id, data }, { onSuccess: () => { invalidate(); setEditingGroup(null); setGroupModal(false); } });
    else createGroup.mutate({ data }, { onSuccess: () => { invalidate(); setGroupModal(false); } });
  };
  const confirmDeleteProduct = (product: ShopProduct) => {
    if (window.confirm(`Delete “${product.name}” from the shop?`)) deleteProduct.mutate({ productId: product.id }, { onSuccess: invalidate });
  };
  const confirmDeleteGroup = (group: ProductGroup) => {
    if (window.confirm(`Delete the “${group.name}” group?`)) deleteGroup.mutate({ groupId: group.id }, { onSuccess: invalidate });
  };
  const busy = createProduct.isPending || updateProduct.isPending;
  const groupBusy = createGroup.isPending || updateGroup.isPending;
  return <div className="fade-in">
    <PageTitle eyebrow="CATALOG / 02" title="Products" description="Shape the catalog customers see inside Telegram." action={<Button testid="button-add-product" onClick={() => { setEditing(null); setProductModal(true); }}><Plus size={16} /> Add product</Button>} />
    <div className="catalog-layout">
      <div className="catalog-main">
        <div className="toolbar"><label className="search-field"><Search size={16} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Find a product…" data-testid="input-product-search" /></label><label className="filter-select"><SlidersHorizontal size={15} /><select value={groupFilter} onChange={(e) => setGroupFilter(e.target.value)} data-testid="select-product-group"><option value="all">All groups</option>{(groups.data || []).map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label></div>
        <Surface className="table-surface">
          {products.isLoading ? <LoadingBlock rows={5} /> : products.isError ? <QueryError message="Product catalog could not be loaded." retry={() => void products.refetch()} /> : !products.data?.length ? <EmptyState icon={Package} title={search || groupFilter !== 'all' ? 'No matching products' : 'Your catalog is empty'} detail={search || groupFilter !== 'all' ? 'Try another search or group.' : 'Add your first product to start building the shop catalog.'} /> :
            <div className="table-scroll"><table><thead><tr><th>PRODUCT</th><th>GROUP</th><th>PRICE</th><th>CONTENT</th><th className="actions-th">ACTIONS</th></tr></thead><tbody>{products.data.map((product) => <tr key={product.id} data-testid={`row-product-${product.id}`}><td><div className="product-name"><span className="product-tile"><Package size={16} /></span><div><strong>{product.name}</strong><small>#{product.id}</small></div></div></td><td><span className="tag">{product.groupName || 'Unassigned'}</span></td><td className="mono amount-cell">{currency(product.price)}</td><td><span className="type-label">{product.contentType || '—'}</span></td><td><div className="row-actions"><button className="icon-button" title="Edit product" onClick={() => { setEditing(product); setProductModal(true); }} data-testid={`button-edit-product-${product.id}`}><Pencil size={15} /></button><button className="icon-button danger-icon" title="Delete product" onClick={() => confirmDeleteProduct(product)} disabled={deleteProduct.isPending} data-testid={`button-delete-product-${product.id}`}><Trash2 size={15} /></button></div></td></tr>)}</tbody></table></div>}
          <ErrorNote error={deleteProduct.error} />
        </Surface>
      </div>
      <Surface className="groups-surface"><div className="surface-heading compact"><div><div className="eyebrow">ORGANIZE</div><h2>Product groups</h2></div><button className="icon-button" title="Add group" onClick={() => { setEditingGroup(null); setGroupModal(true); }} data-testid="button-add-group"><Plus size={17} /></button></div>
        {groups.isLoading ? <LoadingBlock rows={3} /> : groups.isError ? <div className="inline-error">Groups unavailable. <button onClick={() => void groups.refetch()} data-testid="button-retry-groups">Retry</button></div> : !groups.data?.length ? <EmptyState icon={FolderKanban} title="No groups yet" detail="Create a group to organize products." /> : <div className="group-list">{groups.data.map((group) => <div className="group-item" key={group.id} data-testid={`group-${group.id}`}><span className="group-mark"><FolderKanban size={15} /></span><div className="group-copy"><strong>{group.name}</strong><small>{group.productCount} {group.productCount === 1 ? 'product' : 'products'}</small></div><button className="subtle-action" title="Edit group" onClick={() => { setEditingGroup(group); setGroupModal(true); }} data-testid={`button-edit-group-${group.id}`}><Pencil size={13} /></button><button className="subtle-action danger-icon" title="Delete group" onClick={() => confirmDeleteGroup(group)} data-testid={`button-delete-group-${group.id}`}><Trash2 size={13} /></button></div>)}</div>}
        <ErrorNote error={deleteGroup.error} />
        <div className="group-note"><Sparkles size={15} /><span>Groups keep browsing tidy inside the bot.</span></div>
      </Surface>
    </div>
    {productModal && <Modal title={editing ? 'Edit product' : 'Add a product'} description="Changes sync directly to the Telegram storefront." onClose={() => setProductModal(false)} testid="dialog-product">
      <form className="form-stack" onSubmit={saveProduct}>
        <Field label="Product name"><input name="name" defaultValue={editing?.name || ''} required maxLength={180} autoFocus data-testid="input-product-name" /></Field>
        <div className="form-row"><Field label="Price"><input name="price" type="number" min="0" step="0.01" defaultValue={editing?.price ?? ''} required data-testid="input-product-price" /></Field><Field label="Content type"><input name="contentType" defaultValue={editing?.contentType || 'text'} required data-testid="input-product-content-type" /></Field></div>
        <Field label="Delivery content"><textarea name="content" defaultValue={editing?.content || ''} rows={4} data-testid="input-product-content" /></Field>
        <div className="form-row"><Field label="Group"><select name="groupId" defaultValue={editing?.groupId?.toString() || ''} data-testid="select-product-edit-group"><option value="">Unassigned</option>{(groups.data || []).map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></Field><Field label="Photo ID" hint="Optional Telegram file identifier"><input name="photoId" defaultValue={editing?.photoId || ''} data-testid="input-product-photo-id" /></Field></div>
        <ErrorNote error={editing ? updateProduct.error : createProduct.error} />
        <div className="modal-actions"><Button variant="quiet" onClick={() => setProductModal(false)} testid="button-cancel-product">Cancel</Button><Button type="submit" disabled={busy} testid="button-save-product">{busy && <LoaderCircle className="spin" size={15} />}{editing ? 'Save changes' : 'Create product'}</Button></div>
      </form>
    </Modal>}
    {groupModal && <Modal title={editingGroup ? 'Edit group' : 'Create a group'} description="Group products for easy discovery in the shop." onClose={() => setGroupModal(false)} testid="dialog-group">
      <form className="form-stack" onSubmit={saveGroup}><Field label="Group name"><input name="name" required defaultValue={editingGroup?.name || ''} autoFocus data-testid="input-group-name" /></Field><Field label="Parent group"><select name="parentId" defaultValue={editingGroup?.parentId?.toString() || ''} data-testid="select-group-parent"><option value="">No parent</option>{(groups.data || []).filter((g) => g.id !== editingGroup?.id).map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}</select></Field><ErrorNote error={editingGroup ? updateGroup.error : createGroup.error} /><div className="modal-actions"><Button variant="quiet" onClick={() => setGroupModal(false)} testid="button-cancel-group">Cancel</Button><Button type="submit" disabled={groupBusy} testid="button-save-group">{groupBusy ? 'Saving…' : 'Save group'}</Button></div></form>
    </Modal>}
  </div>;
}

function CustomersPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [customer, setCustomer] = useState<ShopCustomer | null>(null);
  const users = useGetAdminUsers({ search: search || undefined });
  const adjust = useAdjustAdminUserBalance();
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!customer) return;
    const form = new FormData(event.currentTarget);
    adjust.mutate({ userId: customer.userId, data: { direction: String(form.get('direction')) as 'credit' | 'debit', amount: Number(form.get('amount')), note: String(form.get('note')).trim() } }, { onSuccess: () => { void qc.invalidateQueries({ queryKey: getGetAdminUsersQueryKey() }); setCustomer(null); } });
  };
  return <div className="fade-in">
    <PageTitle eyebrow="PEOPLE / 03" title="Customers" description="Find Telegram customers and manage their shop balance." />
    <Surface className="people-surface">
      <div className="list-toolbar"><div className="surface-heading compact"><div><div className="eyebrow">CUSTOMER DIRECTORY</div><h2>{users.data?.length ?? '—'} customers</h2></div></div><label className="search-field customer-search"><Search size={16} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Name, username or Telegram ID" data-testid="input-customer-search" /></label></div>
      {users.isLoading ? <LoadingBlock rows={5} /> : users.isError ? <QueryError message="Customer records are unavailable." retry={() => void users.refetch()} /> : !users.data?.length ? <EmptyState icon={Users} title={search ? 'No customer found' : 'No customers yet'} detail={search ? 'Try a username, name or Telegram ID.' : 'Customers who start the shop bot will appear here.'} /> :
        <div className="table-scroll"><table><thead><tr><th>CUSTOMER</th><th>REGISTERED</th><th>ORDERS</th><th>TOTAL SPENT</th><th>SHOP BALANCE</th><th /></tr></thead><tbody>{users.data.map((user) => <tr key={user.userId} data-testid={`row-customer-${user.userId}`}><td><div className="person-cell"><span className="table-avatar">{(user.firstName || user.username || 'R').slice(0, 1).toUpperCase()}</span><div><strong>{personName(user)}</strong><small>{user.username ? `@${user.username} · ` : ''}ID {user.userId}</small></div></div></td><td className="muted-cell">{user.registeredAt ? dateLabel(user.registeredAt).split(',')[0] : '—'}</td><td className="mono">{user.purchaseCount}</td><td className="mono">{currency(user.totalSpent)}</td><td className="mono amount-cell">{currency(user.balance)}</td><td><Button variant="outline" testid={`button-adjust-balance-${user.userId}`} onClick={() => setCustomer(user)}>Adjust balance</Button></td></tr>)}</tbody></table></div>}
    </Surface>
    {customer && <Modal title="Adjust shop balance" description={`Balance for ${personName(customer)} · ${currency(customer.balance)} currently`} onClose={() => setCustomer(null)} testid="dialog-balance">
      <form className="form-stack" onSubmit={submit}><div className="balance-current"><span>Current balance</span><strong>{currency(customer.balance)}</strong></div><Field label="Adjustment"><select name="direction" defaultValue="credit" data-testid="select-balance-direction"><option value="credit">Add funds</option><option value="debit">Deduct funds</option></select></Field><Field label="Amount"><input name="amount" type="number" min="0.01" step="0.01" required data-testid="input-balance-amount" /></Field><Field label="Note"><input name="note" maxLength={250} placeholder="Reason for adjustment" data-testid="input-balance-note" /></Field><ErrorNote error={adjust.error} /><div className="modal-actions"><Button variant="quiet" onClick={() => setCustomer(null)} testid="button-cancel-balance">Cancel</Button><Button type="submit" disabled={adjust.isPending} testid="button-submit-balance">{adjust.isPending ? 'Applying…' : 'Apply adjustment'}</Button></div></form>
    </Modal>}
  </div>;
}

function OrdersPage() {
  const purchases = useGetAdminPurchases({ limit: 200 });
  const total = purchases.data?.reduce((sum, p) => sum + p.price, 0) ?? 0;
  return <div className="fade-in">
    <PageTitle eyebrow="TRANSACTIONS / 04" title="Orders" description="Completed purchases made through your Telegram shop." action={<span className="synced-note"><span className="status-dot" />Completed only</span>} />
    <div className="order-summary"><Surface className="order-stat"><span>HISTORY TOTAL</span><strong>{purchases.data?.length ?? '—'}</strong><small>completed purchases</small></Surface><Surface className="order-stat"><span>GROSS VALUE</span><strong>{purchases.isLoading ? '—' : currency(total)}</strong><small>across loaded history</small></Surface><div className="orders-note"><ShoppingBag size={18} /><p>Purchase history is read-only. New completed orders are recorded by the storefront.</p></div></div>
    <Surface className="orders-surface"><div className="surface-heading"><div><div className="eyebrow">PURCHASE LEDGER</div><h2>All completed purchases</h2></div><span className="record-count mono">{purchases.data?.length ?? 0} RECORDS</span></div>
      {purchases.isLoading ? <LoadingBlock rows={6} /> : purchases.isError ? <QueryError message="Purchase history could not be loaded." retry={() => void purchases.refetch()} /> : !purchases.data?.length ? <EmptyState icon={ShoppingBag} title="No completed orders" detail="When a customer completes a purchase in Telegram, it will be listed here." /> :
        <div className="table-scroll"><table><thead><tr><th>ORDER</th><th>CUSTOMER</th><th>PRODUCT</th><th>AMOUNT</th><th>DATE</th></tr></thead><tbody>{purchases.data.map((purchase) => <tr key={purchase.id} data-testid={`row-order-${purchase.id}`}><td className="mono order-id">#{purchase.id}</td><td><div className="person-cell"><span className="table-avatar">{(purchase.firstName || purchase.username || 'R').slice(0, 1).toUpperCase()}</span><div><strong>{personName(purchase)}</strong><small>ID {purchase.userId}</small></div></div></td><td>{purchase.productName}</td><td className="mono amount-cell">{currency(purchase.price)}</td><td className="muted-cell">{dateLabel(purchase.purchasedAt)}</td></tr>)}</tbody></table></div>}
    </Surface>
  </div>;
}

function PromoPage() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const promos = useGetAdminPromoCodes();
  const create = useCreateAdminPromoCode();
  const remove = useDeleteAdminPromoCode();
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    create.mutate({ data: { code: String(form.get('code')).trim().toUpperCase(), amount: Number(form.get('amount')), usesLeft: Number(form.get('usesLeft')) } }, { onSuccess: () => { void qc.invalidateQueries({ queryKey: getGetAdminPromoCodesQueryKey() }); setOpen(false); } });
  };
  const deleteCode = (code: string) => {
    if (window.confirm(`Remove promo code ${code}?`)) remove.mutate({ code }, { onSuccess: () => void qc.invalidateQueries({ queryKey: getGetAdminPromoCodesQueryKey() }) });
  };
  return <div className="fade-in">
    <PageTitle eyebrow="CAMPAIGNS / 05" title="Promo codes" description="Create and retire offers for your Telegram customers." action={<Button testid="button-create-promo" onClick={() => setOpen(true)}><Plus size={16} /> Create code</Button>} />
    <div className="promo-banner"><div className="promo-banner-mark"><BadgePercent size={21} /></div><div><span className="eyebrow">SHOP INCENTIVES</span><strong>Small codes. Clear rules.</strong><p>Every code has a fixed amount and a finite number of uses.</p></div><div className="promo-banner-count"><strong>{promos.data?.length ?? '—'}</strong><span>ACTIVE CODES</span></div></div>
    <Surface className="promo-surface"><div className="surface-heading"><div><div className="eyebrow">OFFER REGISTER</div><h2>Active promo codes</h2></div><span className="record-count mono">{promos.data?.length ?? 0} ACTIVE</span></div>
      {promos.isLoading ? <LoadingBlock rows={4} /> : promos.isError ? <QueryError message="Promo codes could not be loaded." retry={() => void promos.refetch()} /> : !promos.data?.length ? <EmptyState icon={BadgePercent} title="No active codes" detail="Create a promo code to give customers a reason to come back." /> :
        <div className="promo-list">{promos.data.map((promo) => <div className="promo-item" key={promo.code} data-testid={`promo-${promo.code}`}><span className="promo-ticket"><BadgePercent size={18} /></span><div className="promo-code"><strong>{promo.code}</strong><small>Fixed value offer</small></div><div className="promo-amount"><span>VALUE</span><strong>{currency(promo.amount)}</strong></div><div className="promo-uses"><span>USES LEFT</span><strong>{promo.usesLeft.toLocaleString()}</strong></div><div className="promo-visual"><span style={{ width: `${Math.max(4, Math.min(100, promo.usesLeft * 8))}%` }} /></div><button className="icon-button danger-icon" title="Delete promo code" onClick={() => deleteCode(promo.code)} disabled={remove.isPending} data-testid={`button-delete-promo-${promo.code}`}><Trash2 size={15} /></button></div>)}</div>}
      <ErrorNote error={remove.error} />
    </Surface>
    {open && <Modal title="Create promo code" description="Add a fixed-value code with a finite use count." onClose={() => setOpen(false)} testid="dialog-promo"><form className="form-stack" onSubmit={submit}><Field label="Code" hint="Customers enter this in the shop"><input name="code" required maxLength={64} autoFocus placeholder="WELCOME10" data-testid="input-promo-code" /></Field><div className="form-row"><Field label="Value"><input name="amount" type="number" min="0.01" step="0.01" required data-testid="input-promo-amount" /></Field><Field label="Uses available"><input name="usesLeft" type="number" min="1" step="1" required data-testid="input-promo-uses" /></Field></div><ErrorNote error={create.error} /><div className="modal-actions"><Button variant="quiet" onClick={() => setOpen(false)} testid="button-cancel-promo">Cancel</Button><Button type="submit" disabled={create.isPending} testid="button-save-promo">{create.isPending ? 'Creating…' : 'Create code'}</Button></div></form></Modal>}
  </div>;
}

function SettingsPage() {
  const qc = useQueryClient();
  const settings = useGetAdminSettings();
  const update = useUpdateAdminSettings();
  const [support, setSupport] = useState('');
  const [channel, setChannel] = useState('');
  const [initialized, setInitialized] = useState(false);
  useEffect(() => {
    if (settings.data && !initialized) {
      setSupport(settings.data.supportLink || '');
      setChannel(settings.data.infoChannel || '');
      setInitialized(true);
    }
  }, [settings.data, initialized]);
  const saveLinks = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    update.mutate({ data: { supportLink: support.trim(), infoChannel: channel.trim() } }, { onSuccess: () => void qc.invalidateQueries({ queryKey: getGetAdminSettingsQueryKey() }) });
  };
  const toggleMaintenance = () => {
    if (!settings.data) return;
    update.mutate({ data: { maintenance: !settings.data.maintenance } }, { onSuccess: () => void qc.invalidateQueries({ queryKey: getGetAdminSettingsQueryKey() }) });
  };
  return <div className="fade-in">
    <PageTitle eyebrow="SHOP CONFIGURATION / 06" title="Settings" description="Control storefront availability and its public links." />
    {settings.isLoading ? <LoadingBlock rows={5} /> : settings.isError || !settings.data ? <QueryError message="Shop settings could not be loaded." retry={() => void settings.refetch()} /> : <>
      <Surface className={`maintenance-panel ${settings.data.maintenance ? 'maintenance-on' : ''}`}><div className="maintenance-symbol">{settings.data.maintenance ? <ShieldAlert size={21} /> : <Check size={21} />}</div><div className="maintenance-copy"><span className="eyebrow">STOREFRONT STATUS</span><h2>{settings.data.maintenance ? 'Maintenance mode is on' : 'Your shop is open'}</h2><p>{settings.data.maintenance ? 'Customers cannot make purchases while maintenance mode is active.' : 'Customers can browse and purchase from the Telegram shop.'}</p></div><div className="maintenance-control"><span className={`status-pill ${settings.data.maintenance ? 'status-paused' : ''}`}><span />{settings.data.maintenance ? 'PAUSED' : 'LIVE'}</span><Button variant={settings.data.maintenance ? 'primary' : 'outline'} disabled={update.isPending} onClick={toggleMaintenance} testid="button-toggle-maintenance">{update.isPending ? 'Updating…' : settings.data.maintenance ? 'Resume shop' : 'Pause shop'}</Button></div></Surface>
      {update.isError && <div className="settings-error"><ErrorNote error={update.error} /></div>}
      <div className="settings-grid"><Surface className="settings-form-surface"><div className="surface-heading"><div><div className="eyebrow">CUSTOMER DESTINATIONS</div><h2>Public links</h2></div><span className="heading-icon"><Link2 size={17} /></span></div><p className="section-intro">These links are shared with customers from the Telegram shop.</p><form className="form-stack" onSubmit={saveLinks}><Field label="Support link" hint="Support contact or support chat URL"><input type="url" value={support} onChange={(e) => setSupport(e.target.value)} placeholder="https://t.me/ricerve_support" data-testid="input-support-link" /></Field><Field label="Information channel" hint="Your shop updates and announcements"><input type="url" value={channel} onChange={(e) => setChannel(e.target.value)} placeholder="https://t.me/ricerve_news" data-testid="input-info-channel" /></Field><ErrorNote error={update.error} /><div className="settings-save"><span>{update.isSuccess ? <><Check size={14} /> Changes saved</> : 'Remember to save your changes'}</span><Button type="submit" disabled={update.isPending} testid="button-save-settings">{update.isPending ? 'Saving…' : 'Save links'}</Button></div></form></Surface>
        <div className="settings-aside"><Surface className="link-preview"><div className="eyebrow">LINK CHECK</div><h3>Shop destinations</h3><div className="preview-link"><span className="preview-icon"><CircleHelp size={16} /></span><div><small>SUPPORT</small><strong>{settings.data.supportLink || 'Not configured'}</strong></div>{settings.data.supportLink && <a href={settings.data.supportLink} target="_blank" rel="noreferrer" aria-label="Open support link" data-testid="link-support-external"><ExternalLink size={14} /></a>}</div><div className="preview-link"><span className="preview-icon channel"><Command size={16} /></span><div><small>INFO CHANNEL</small><strong>{settings.data.infoChannel || 'Not configured'}</strong></div>{settings.data.infoChannel && <a href={settings.data.infoChannel} target="_blank" rel="noreferrer" aria-label="Open info channel" data-testid="link-channel-external"><ExternalLink size={14} /></a>}</div></Surface><Surface className="settings-tip"><span><Activity size={17} /></span><div><strong>Connected to Telegram</strong><p>Shop settings apply to the storefront without moving customer interactions out of the bot.</p></div></Surface></div>
      </div>
    </>}
  </div>;
}

function RoutedErrorBoundary({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  return <ErrorBoundary resetKey={location}>{children}</ErrorBoundary>;
}
function Router() {
  return <RoutedErrorBoundary><AuthGate /></RoutedErrorBoundary>;
}
function App() {
  return <QueryClientProvider client={queryClient}><TooltipProvider><WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}><Router /></WouterRouter><Toaster /></TooltipProvider></QueryClientProvider>;
}
export default App;