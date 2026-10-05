import { createHmac, timingSafeEqual } from "node:crypto";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { DatabaseSync } from "node:sqlite";
import { Router, type IRouter, type NextFunction, type Request, type Response } from "express";
import {
  AdjustAdminUserBalanceBody,
  AdjustAdminUserBalanceParams,
  AdjustAdminUserBalanceResponse,
  CreateAdminGroupBody,
  CreateAdminGroupResponse,
  CreateAdminProductBody,
  CreateAdminProductResponse,
  CreateAdminPromoCodeBody,
  CreateAdminPromoCodeResponse,
  DeleteAdminGroupParams,
  DeleteAdminProductParams,
  DeleteAdminPromoCodeParams,
  GetAdminAuthResponse,
  GetAdminDashboardResponse,
  GetAdminGroupsResponse,
  GetAdminProductsQueryParams,
  GetAdminProductsResponse,
  GetAdminPromoCodesResponse,
  GetAdminPurchasesQueryParams,
  GetAdminPurchasesResponse,
  GetAdminSettingsResponse,
  GetAdminUsersQueryParams,
  GetAdminUsersResponse,
  ProductUpdate,
  ShopSettingsUpdate,
  UpdateAdminGroupBody,
  UpdateAdminGroupParams,
  UpdateAdminGroupResponse,
  UpdateAdminProductBody,
  UpdateAdminProductParams,
  UpdateAdminProductResponse,
  UpdateAdminSettingsBody,
  UpdateAdminSettingsResponse,
} from "@workspace/api-zod";

const router: IRouter = Router();

type SqlRow = Record<string, string | number | bigint | null>;
type AdminRequest = Request & { adminUserId?: number };
type TelegramIdentity = { userId: number; username: string | null };
type AuthResult =
  | { ok: true; identity: TelegramIdentity }
  | { ok: false; reason: string };

let database: DatabaseSync | undefined;

function getDatabasePath(): string {
  return process.env.SHOP_DB_PATH
    ? resolve(process.env.SHOP_DB_PATH)
    : resolve(process.cwd(), "../../shop-bot/shop.db");
}

function getDatabase(): DatabaseSync {
  if (!database) {
    const path = getDatabasePath();
    const parent = resolve(path, "..");
    if (!existsSync(parent)) {
      throw new Error(`Shop database directory does not exist: ${parent}`);
    }
    database = new DatabaseSync(path);
    database.exec("PRAGMA busy_timeout = 5000");
  }
  return database;
}

function ensureShopTables(): void {
  const ready = getDatabase()
    .prepare("SELECT 1 AS ready FROM sqlite_master WHERE type = 'table' AND name = 'users'")
    .get();
  if (!ready) {
    throw new Error("SHOP_DATABASE_NOT_INITIALIZED");
  }
}

function row<T extends SqlRow = SqlRow>(value: unknown): T | undefined {
  return value as T | undefined;
}

function records<T extends SqlRow = SqlRow>(value: unknown): T[] {
  return value as T[];
}

function normalizedDate(value: string | null): string | null {
  if (!value) return null;
  return value.includes("T") ? value : `${value.replace(" ", "T")}Z`;
}

function authFromRequest(req: Request): AuthResult {
  const initData = req.get("X-Telegram-Init-Data");
  const token = process.env.BOT_TOKEN;
  if (!token) return { ok: false, reason: "bot_token_not_configured" };
  if (!initData) return { ok: false, reason: "telegram_init_data_missing" };

  try {
    const fields = new URLSearchParams(initData);
    const receivedHash = fields.get("hash");
    const authDate = Number(fields.get("auth_date"));
    const userJson = fields.get("user");
    if (!receivedHash || !userJson || !Number.isFinite(authDate)) {
      return { ok: false, reason: "telegram_init_data_invalid" };
    }

    const now = Math.floor(Date.now() / 1000);
    if (authDate > now + 60 || now - authDate > 86_400) {
      return { ok: false, reason: "telegram_init_data_expired" };
    }

    const dataCheckString = [...fields.entries()]
      .filter(([key]) => key !== "hash")
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, value]) => `${key}=${value}`)
      .join("\n");
    const secretKey = createHmac("sha256", "WebAppData").update(token).digest();
    const expectedHash = createHmac("sha256", secretKey)
      .update(dataCheckString)
      .digest();
    const actualHash = Buffer.from(receivedHash, "hex");
    if (actualHash.length !== expectedHash.length || !timingSafeEqual(actualHash, expectedHash)) {
      return { ok: false, reason: "telegram_init_data_invalid" };
    }

    const telegramUser = JSON.parse(userJson) as { id?: unknown; username?: unknown };
    const userId = Number(telegramUser.id);
    if (!Number.isSafeInteger(userId) || userId <= 0) {
      return { ok: false, reason: "telegram_user_invalid" };
    }
    return {
      ok: true,
      identity: {
        userId,
        username: typeof telegramUser.username === "string" ? telegramUser.username : null,
      },
    };
  } catch {
    return { ok: false, reason: "telegram_init_data_invalid" };
  }
}

function isAdministrator(userId: number): boolean {
  const configuredIds = (process.env.ADMIN_IDS ?? "8630192662")
    .split(",")
    .map((value) => Number(value.trim()))
    .filter(Number.isSafeInteger);
  if (configuredIds.includes(userId)) return true;

  try {
    const db = getDatabase();
    const hasAdminsTable = db
      .prepare("SELECT 1 AS found FROM sqlite_master WHERE type = 'table' AND name = 'admins'")
      .get();
    if (!hasAdminsTable) return false;
    return Boolean(db.prepare("SELECT 1 FROM admins WHERE user_id = ?").get(userId));
  } catch {
    return false;
  }
}

function requireAdministrator(req: Request, res: Response, next: NextFunction): void {
  const auth = authFromRequest(req);
  if (!auth.ok) {
    res.status(401).json({ error: auth.reason });
    return;
  }
  if (!isAdministrator(auth.identity.userId)) {
    res.status(403).json({ error: "telegram_user_not_admin" });
    return;
  }
  (req as AdminRequest).adminUserId = auth.identity.userId;
  try {
    ensureShopTables();
  } catch {
    res.status(503).json({ error: "shop_database_not_initialized" });
    return;
  }
  next();
}

function parseId(raw: string | string[]): number | null {
  const value = Array.isArray(raw) ? raw[0] : raw;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null;
}

function parseError(res: Response, error: { message: string }): void {
  res.status(400).json({ error: error.message });
}

function validateParentGroup(parentId: number | null, currentGroupId?: number): boolean {
  if (parentId === null) return true;
  if (parentId === currentGroupId) return false;
  const db = getDatabase();
  const parentExists = db.prepare("SELECT 1 FROM product_groups WHERE id = ?").get(parentId);
  if (!parentExists) return false;
  if (currentGroupId === undefined) return true;

  const cycle = db
    .prepare(
      `WITH RECURSIVE descendants(id) AS (
         SELECT id FROM product_groups WHERE id = ?
         UNION ALL
         SELECT groups.id FROM product_groups groups
         JOIN descendants ON groups.parent_id = descendants.id
       )
       SELECT 1 FROM descendants WHERE id = ? LIMIT 1`,
    )
    .get(currentGroupId, parentId);
  return !cycle;
}

function getProduct(productId: number): SqlRow | undefined {
  return row(
    getDatabase()
      .prepare(
        `SELECT products.id, products.name, products.price, products.content,
                products.content_type AS contentType, products.group_id AS groupId,
                groups.name AS groupName, products.photo_id AS photoId
         FROM products
         LEFT JOIN product_groups groups ON groups.id = products.group_id
         WHERE products.id = ?`,
      )
      .get(productId),
  );
}

function getGroup(groupId: number): SqlRow | undefined {
  return row(
    getDatabase()
      .prepare(
        `SELECT groups.id, groups.name, groups.parent_id AS parentId,
                COUNT(products.id) AS productCount
         FROM product_groups groups
         LEFT JOIN products ON products.group_id = groups.id
         WHERE groups.id = ?
         GROUP BY groups.id`,
      )
      .get(groupId),
  );
}

function listPurchases(limit: number): SqlRow[] {
  const result = records(
    getDatabase()
      .prepare(
        `SELECT purchases.id, purchases.user_id AS userId,
                users.username, users.first_name AS firstName,
                purchases.product_id AS productId, purchases.product_name AS productName,
                purchases.price, purchases.purchased_at AS purchasedAt
         FROM purchases
         LEFT JOIN users ON users.user_id = purchases.user_id
         ORDER BY purchases.purchased_at DESC, purchases.id DESC
         LIMIT ?`,
      )
      .all(limit),
  );
  return result.map((purchase) => ({
    ...purchase,
    purchasedAt: normalizedDate(typeof purchase.purchasedAt === "string" ? purchase.purchasedAt : null),
  }));
}

function setting(key: string, fallback: string): string {
  const found = row(getDatabase().prepare("SELECT value FROM settings WHERE key = ?").get(key));
  return typeof found?.value === "string" ? found.value : fallback;
}

function saveSetting(key: string, value: string): void {
  getDatabase()
    .prepare("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value")
    .run(key, value);
}

router.get("/admin/auth", (req, res): void => {
  const auth = authFromRequest(req);
  if (!auth.ok) {
    res.json(
      GetAdminAuthResponse.parse({
        authorized: false,
        reason: auth.reason,
        username: null,
      }),
    );
    return;
  }
  if (!isAdministrator(auth.identity.userId)) {
    res.json(
      GetAdminAuthResponse.parse({
        authorized: false,
        reason: "telegram_user_not_admin",
        username: null,
      }),
    );
    return;
  }
  res.json(
    GetAdminAuthResponse.parse({
      authorized: true,
      reason: null,
      username: auth.identity.username,
    }),
  );
});

router.use("/admin", (req, res, next) => {
  if (req.method === "GET" && req.path === "/auth") {
    next();
    return;
  }
  requireAdministrator(req, res, next);
});

router.get("/admin/dashboard", (_req, res): void => {
  const db = getDatabase();
  const users = row(db.prepare("SELECT COUNT(*) AS total FROM users").get());
  const active = row(
    db
      .prepare("SELECT COUNT(*) AS total FROM users WHERE last_active >= datetime('now', '-24 hours')")
      .get(),
  );
  const products = row(db.prepare("SELECT COUNT(*) AS total FROM products").get());
  const purchases = row(
    db.prepare("SELECT COUNT(*) AS total, COALESCE(SUM(price), 0) AS revenue FROM purchases").get(),
  );
  const pending = row(
    db.prepare("SELECT COUNT(*) AS total FROM payments WHERE status = 'pending'").get(),
  );

  res.json(
    GetAdminDashboardResponse.parse({
      totalUsers: Number(users?.total ?? 0),
      activeUsers: Number(active?.total ?? 0),
      totalProducts: Number(products?.total ?? 0),
      totalPurchases: Number(purchases?.total ?? 0),
      grossRevenue: Number(purchases?.revenue ?? 0),
      pendingPayments: Number(pending?.total ?? 0),
      recentPurchases: listPurchases(8),
    }),
  );
});

router.get("/admin/products", (req, res): void => {
  const params = GetAdminProductsQueryParams.safeParse(req.query);
  if (!params.success) {
    parseError(res, params.error);
    return;
  }
  const db = getDatabase();
  const clauses: string[] = [];
  const values: Array<string | number> = [];
  const search = params.data.search?.trim();
  if (search) {
    clauses.push("lower(products.name) LIKE lower(?)");
    values.push(`%${search}%`);
  }
  if (params.data.groupId !== undefined) {
    clauses.push("products.group_id = ?");
    values.push(params.data.groupId);
  }
  const where = clauses.length ? `WHERE ${clauses.join(" AND ")}` : "";
  const products = records(
    db
      .prepare(
        `SELECT products.id, products.name, products.price, products.content,
                products.content_type AS contentType, products.group_id AS groupId,
                groups.name AS groupName, products.photo_id AS photoId
         FROM products
         LEFT JOIN product_groups groups ON groups.id = products.group_id
         ${where}
         ORDER BY products.id DESC`,
      )
      .all(...values),
  );
  res.json(GetAdminProductsResponse.parse(products));
});

router.post("/admin/products", (req, res): void => {
  const input = CreateAdminProductBody.safeParse(req.body);
  if (!input.success) {
    parseError(res, input.error);
    return;
  }
  const value = input.data;
  if (value.groupId !== null && !getDatabase().prepare("SELECT 1 FROM product_groups WHERE id = ?").get(value.groupId)) {
    res.status(400).json({ error: "product_group_not_found" });
    return;
  }
  const created = getDatabase()
    .prepare(
      `INSERT INTO products (name, price, content, content_type, group_id, photo_id)
       VALUES (?, ?, ?, ?, ?, ?)`,
    )
    .run(value.name.trim(), value.price, value.content, value.contentType, value.groupId, value.photoId);
  const product = getProduct(Number(created.lastInsertRowid));
  res.status(201).json(CreateAdminProductResponse.parse(product));
});

router.patch("/admin/products/:productId", (req, res): void => {
  const params = UpdateAdminProductParams.safeParse(req.params);
  const input = UpdateAdminProductBody.safeParse(req.body);
  if (!params.success) {
    parseError(res, params.error);
    return;
  }
  if (!input.success) {
    parseError(res, input.error);
    return;
  }
  const productId = params.data.productId;
  const current = getProduct(productId);
  if (!current) {
    res.status(404).json({ error: "product_not_found" });
    return;
  }
  const updates = input.data as ProductUpdate;
  const fields: Array<[keyof ProductUpdate, string]> = [
    ["name", "name"],
    ["price", "price"],
    ["content", "content"],
    ["contentType", "content_type"],
    ["groupId", "group_id"],
    ["photoId", "photo_id"],
  ];
  const selected = fields.filter(([key]) => Object.hasOwn(updates, key));
  if (selected.length === 0) {
    res.status(400).json({ error: "no_product_fields_to_update" });
    return;
  }
  const groupId = updates.groupId;
  if (groupId !== undefined && groupId !== null && !getDatabase().prepare("SELECT 1 FROM product_groups WHERE id = ?").get(groupId)) {
    res.status(400).json({ error: "product_group_not_found" });
    return;
  }
  const values = selected.map(([key]) => {
    const value = updates[key];
    if (value === undefined) {
      throw new Error("Unexpected missing product field");
    }
    return key === "name" && typeof value === "string" ? value.trim() : value;
  });
  getDatabase()
    .prepare(`UPDATE products SET ${selected.map(([, column]) => `${column} = ?`).join(", ")} WHERE id = ?`)
    .run(...values, productId);
  res.json(UpdateAdminProductResponse.parse(getProduct(productId)));
});

router.delete("/admin/products/:productId", (req, res): void => {
  const params = DeleteAdminProductParams.safeParse(req.params);
  if (!params.success) {
    parseError(res, params.error);
    return;
  }
  const result = getDatabase().prepare("DELETE FROM products WHERE id = ?").run(params.data.productId);
  if (Number(result.changes) === 0) {
    res.status(404).json({ error: "product_not_found" });
    return;
  }
  res.status(204).send();
});

router.get("/admin/groups", (_req, res): void => {
  const groups = records(
    getDatabase()
      .prepare(
        `SELECT groups.id, groups.name, groups.parent_id AS parentId,
                COUNT(products.id) AS productCount
         FROM product_groups groups
         LEFT JOIN products ON products.group_id = groups.id
         GROUP BY groups.id
         ORDER BY groups.parent_id IS NOT NULL, groups.parent_id, groups.id`,
      )
      .all(),
  );
  res.json(GetAdminGroupsResponse.parse(groups));
});

router.post("/admin/groups", (req, res): void => {
  const input = CreateAdminGroupBody.safeParse(req.body);
  if (!input.success) {
    parseError(res, input.error);
    return;
  }
  if (!validateParentGroup(input.data.parentId)) {
    res.status(400).json({ error: "product_group_parent_invalid" });
    return;
  }
  try {
    const result = getDatabase()
      .prepare("INSERT INTO product_groups (name, parent_id) VALUES (?, ?)")
      .run(input.data.name.trim(), input.data.parentId);
    res.status(201).json(CreateAdminGroupResponse.parse(getGroup(Number(result.lastInsertRowid))));
  } catch {
    res.status(409).json({ error: "product_group_name_exists" });
  }
});

router.patch("/admin/groups/:groupId", (req, res): void => {
  const params = UpdateAdminGroupParams.safeParse(req.params);
  const input = UpdateAdminGroupBody.safeParse(req.body);
  if (!params.success) {
    parseError(res, params.error);
    return;
  }
  if (!input.success) {
    parseError(res, input.error);
    return;
  }
  const current = getGroup(params.data.groupId);
  if (!current) {
    res.status(404).json({ error: "product_group_not_found" });
    return;
  }
  const updates = input.data as { name?: string; parentId?: number | null };
  const columns: Array<[keyof typeof updates, string]> = [["name", "name"], ["parentId", "parent_id"]];
  const selected = columns.filter(([key]) => Object.hasOwn(updates, key));
  if (selected.length === 0) {
    res.status(400).json({ error: "no_group_fields_to_update" });
    return;
  }
  if (updates.parentId !== undefined && !validateParentGroup(updates.parentId, params.data.groupId)) {
    res.status(400).json({ error: "product_group_parent_invalid" });
    return;
  }
  const values = selected.map(([key]) => {
    const value = updates[key];
    if (value === undefined) {
      throw new Error("Unexpected missing group field");
    }
    return key === "name" && typeof value === "string" ? value.trim() : value;
  });
  try {
    getDatabase()
      .prepare(`UPDATE product_groups SET ${selected.map(([, column]) => `${column} = ?`).join(", ")} WHERE id = ?`)
      .run(...values, params.data.groupId);
  } catch {
    res.status(409).json({ error: "product_group_name_exists" });
    return;
  }
  res.json(UpdateAdminGroupResponse.parse(getGroup(params.data.groupId)));
});

router.delete("/admin/groups/:groupId", (req, res): void => {
  const params = DeleteAdminGroupParams.safeParse(req.params);
  if (!params.success) {
    parseError(res, params.error);
    return;
  }
  const db = getDatabase();
  if (!getGroup(params.data.groupId)) {
    res.status(404).json({ error: "product_group_not_found" });
    return;
  }
  db.exec("BEGIN IMMEDIATE");
  try {
    const descendants = db.prepare(
      `WITH RECURSIVE descendants(id) AS (
         SELECT id FROM product_groups WHERE id = ?
         UNION ALL
         SELECT groups.id FROM product_groups groups
         JOIN descendants ON groups.parent_id = descendants.id
       )
       SELECT id FROM descendants`,
    ).all(params.data.groupId) as Array<{ id: number }>;
    const ids = descendants.map((item) => item.id);
    for (const id of ids) {
      db.prepare("UPDATE products SET group_id = NULL WHERE group_id = ?").run(id);
    }
    for (const id of [...ids].reverse()) {
      db.prepare("DELETE FROM product_groups WHERE id = ?").run(id);
    }
    db.exec("COMMIT");
  } catch (error) {
    db.exec("ROLLBACK");
    throw error;
  }
  res.status(204).send();
});

router.get("/admin/users", (req, res): void => {
  const params = GetAdminUsersQueryParams.safeParse(req.query);
  if (!params.success) {
    parseError(res, params.error);
    return;
  }
  const search = params.data.search?.trim();
  const values: string[] = [];
  const where = search
    ? "WHERE CAST(users.user_id AS TEXT) LIKE ? OR users.username LIKE ? COLLATE NOCASE OR users.first_name LIKE ? COLLATE NOCASE"
    : "";
  if (search) values.push(`%${search}%`, `%${search}%`, `%${search}%`);
  const customers = records(
    getDatabase()
      .prepare(
        `SELECT users.user_id AS userId, users.username, users.first_name AS firstName,
                users.balance, users.registered_at AS registeredAt, users.last_active AS lastActive,
                COUNT(purchases.id) AS purchaseCount, COALESCE(SUM(purchases.price), 0) AS totalSpent
         FROM users
         LEFT JOIN purchases ON purchases.user_id = users.user_id
         ${where}
         GROUP BY users.user_id
         ORDER BY users.last_active DESC, users.user_id DESC
         LIMIT 500`,
      )
      .all(...values),
  ).map((customer) => ({
    ...customer,
    registeredAt: normalizedDate(typeof customer.registeredAt === "string" ? customer.registeredAt : null),
    lastActive: normalizedDate(typeof customer.lastActive === "string" ? customer.lastActive : null),
  }));
  res.json(GetAdminUsersResponse.parse(customers));
});

router.post("/admin/users/:userId/balance", (req, res): void => {
  const params = AdjustAdminUserBalanceParams.safeParse(req.params);
  const input = AdjustAdminUserBalanceBody.safeParse(req.body);
  if (!params.success) {
    parseError(res, params.error);
    return;
  }
  if (!input.success) {
    parseError(res, input.error);
    return;
  }
  const adminUserId = (req as AdminRequest).adminUserId;
  if (adminUserId === undefined) {
    res.status(401).json({ error: "telegram_init_data_missing" });
    return;
  }
  const db = getDatabase();
  const userId = params.data.userId;
  let failure: "customer_not_found" | "balance_cannot_be_negative" | null = null;
  let after: number | null = null;
  db.exec("BEGIN IMMEDIATE");
  try {
    const user = row(db.prepare("SELECT balance FROM users WHERE user_id = ?").get(userId));
    if (!user) {
      failure = "customer_not_found";
    } else {
      const before = Number(user.balance ?? 0);
      const delta = input.data.direction === "credit" ? input.data.amount : -input.data.amount;
      after = Math.round((before + delta + Number.EPSILON) * 100) / 100;
      if (after < 0) {
        failure = "balance_cannot_be_negative";
      } else {
        db.prepare("UPDATE users SET balance = ? WHERE user_id = ?").run(after, userId);
        db.prepare(
          `INSERT INTO balance_adjustments
           (admin_user_id, user_id, direction, amount, note, previous_balance, new_balance)
           VALUES (?, ?, ?, ?, ?, ?, ?)`,
        ).run(
          adminUserId,
          userId,
          input.data.direction,
          input.data.amount,
          input.data.note.trim(),
          before,
          after,
        );
      }
    }
    if (failure) {
      db.exec("ROLLBACK");
    } else {
      db.exec("COMMIT");
    }
  } catch (error) {
    db.exec("ROLLBACK");
    throw error;
  }
  if (failure === "customer_not_found") {
    res.status(404).json({ error: failure });
    return;
  }
  if (failure === "balance_cannot_be_negative" || after === null) {
    res.status(409).json({ error: "balance_cannot_be_negative" });
    return;
  }
  res.json(AdjustAdminUserBalanceResponse.parse({ userId, balance: after }));
});

router.get("/admin/purchases", (req, res): void => {
  const params = GetAdminPurchasesQueryParams.safeParse(req.query);
  if (!params.success) {
    parseError(res, params.error);
    return;
  }
  res.json(GetAdminPurchasesResponse.parse(listPurchases(params.data.limit ?? 100)));
});

router.get("/admin/promocodes", (_req, res): void => {
  const promos = records(
    getDatabase()
      .prepare("SELECT code, amount, uses_left AS usesLeft FROM promo_codes ORDER BY code")
      .all(),
  );
  res.json(GetAdminPromoCodesResponse.parse(promos));
});

router.post("/admin/promocodes", (req, res): void => {
  const input = CreateAdminPromoCodeBody.safeParse(req.body);
  if (!input.success) {
    parseError(res, input.error);
    return;
  }
  const value = input.data;
  try {
    getDatabase()
      .prepare("INSERT INTO promo_codes (code, amount, uses_left) VALUES (?, ?, ?)")
      .run(value.code.trim(), value.amount, value.usesLeft);
  } catch {
    res.status(409).json({ error: "promo_code_already_exists" });
    return;
  }
  res.status(201).json(CreateAdminPromoCodeResponse.parse(value));
});

router.delete("/admin/promocodes/:code", (req, res): void => {
  const params = DeleteAdminPromoCodeParams.safeParse(req.params);
  if (!params.success) {
    parseError(res, params.error);
    return;
  }
  const result = getDatabase()
    .prepare("DELETE FROM promo_codes WHERE code = ?")
    .run(params.data.code);
  if (Number(result.changes) === 0) {
    res.status(404).json({ error: "promo_code_not_found" });
    return;
  }
  res.status(204).send();
});

router.get("/admin/settings", (_req, res): void => {
  res.json(
    GetAdminSettingsResponse.parse({
      maintenance: setting("maintenance", "0") === "1",
      supportLink: setting("support_link", process.env.SUPPORT_LINK ?? "https://t.me/seoload"),
      infoChannel: setting("info_channel", process.env.INFO_CHANNEL ?? "https://t.me/ricershop"),
    }),
  );
});

router.patch("/admin/settings", (req, res): void => {
  const input = UpdateAdminSettingsBody.safeParse(req.body);
  if (!input.success) {
    parseError(res, input.error);
    return;
  }
  const update = input.data as ShopSettingsUpdate;
  if (Object.hasOwn(update, "maintenance")) {
    saveSetting("maintenance", update.maintenance ? "1" : "0");
  }
  if (typeof update.supportLink === "string") {
    saveSetting("support_link", update.supportLink.trim());
  }
  if (typeof update.infoChannel === "string") {
    saveSetting("info_channel", update.infoChannel.trim());
  }
  res.json(
    UpdateAdminSettingsResponse.parse({
      maintenance: setting("maintenance", "0") === "1",
      supportLink: setting("support_link", process.env.SUPPORT_LINK ?? "https://t.me/seoload"),
      infoChannel: setting("info_channel", process.env.INFO_CHANNEL ?? "https://t.me/ricershop"),
    }),
  );
});

export default router;
