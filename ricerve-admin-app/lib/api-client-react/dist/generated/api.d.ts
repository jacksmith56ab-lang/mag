import type { QueryKey, UseMutationOptions, UseMutationResult, UseQueryOptions, UseQueryResult } from '@tanstack/react-query';
import type { AdminAuth, BalanceAdjustment, BalanceResult, DashboardSummary, GetAdminProductsParams, GetAdminPurchasesParams, GetAdminUsersParams, HealthStatus, ProductGroup, ProductGroupInput, ProductGroupUpdate, ProductInput, ProductUpdate, PromoCode, PromoCodeInput, ShopCustomer, ShopProduct, ShopPurchase, ShopSettings, ShopSettingsUpdate } from './api.schemas';
import { customFetch } from '../custom-fetch';
import type { ErrorType, BodyType } from '../custom-fetch';
type AwaitedInput<T> = PromiseLike<T> | T;
type Awaited<O> = O extends AwaitedInput<infer T> ? T : never;
type SecondParameter<T extends (...args: never) => unknown> = Parameters<T>[1];
export declare const getHealthCheckUrl: () => string;
/**
 * Returns server health status
 * @summary Health check
 */
export declare const healthCheck: (options?: Parameters<typeof customFetch>[1]) => Promise<HealthStatus>;
export declare const getHealthCheckQueryKey: () => readonly ["/api/healthz"];
export declare const getHealthCheckQueryOptions: <TData = Awaited<ReturnType<typeof healthCheck>>, TError = ErrorType<unknown>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof healthCheck>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}) => UseQueryOptions<Awaited<ReturnType<typeof healthCheck>>, TError, TData> & {
    queryKey: QueryKey;
};
export type HealthCheckQueryResult = NonNullable<Awaited<ReturnType<typeof healthCheck>>>;
export type HealthCheckQueryError = ErrorType<unknown>;
/**
 * @summary Health check
 */
export declare function useHealthCheck<TData = Awaited<ReturnType<typeof healthCheck>>, TError = ErrorType<unknown>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof healthCheck>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}): UseQueryResult<TData, TError> & {
    queryKey: QueryKey;
};
export declare const getGetAdminAuthUrl: () => string;
/**
 * @summary Check Telegram Mini App authorization
 */
export declare const getAdminAuth: (options?: Parameters<typeof customFetch>[1]) => Promise<AdminAuth>;
export declare const getGetAdminAuthQueryKey: () => readonly ["/api/admin/auth"];
export declare const getGetAdminAuthQueryOptions: <TData = Awaited<ReturnType<typeof getAdminAuth>>, TError = ErrorType<unknown>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getAdminAuth>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}) => UseQueryOptions<Awaited<ReturnType<typeof getAdminAuth>>, TError, TData> & {
    queryKey: QueryKey;
};
export type GetAdminAuthQueryResult = NonNullable<Awaited<ReturnType<typeof getAdminAuth>>>;
export type GetAdminAuthQueryError = ErrorType<unknown>;
/**
 * @summary Check Telegram Mini App authorization
 */
export declare function useGetAdminAuth<TData = Awaited<ReturnType<typeof getAdminAuth>>, TError = ErrorType<unknown>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getAdminAuth>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}): UseQueryResult<TData, TError> & {
    queryKey: QueryKey;
};
export declare const getGetAdminDashboardUrl: () => string;
/**
 * @summary Read live shop totals and recent purchases
 */
export declare const getAdminDashboard: (options?: Parameters<typeof customFetch>[1]) => Promise<DashboardSummary>;
export declare const getGetAdminDashboardQueryKey: () => readonly ["/api/admin/dashboard"];
export declare const getGetAdminDashboardQueryOptions: <TData = Awaited<ReturnType<typeof getAdminDashboard>>, TError = ErrorType<unknown>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getAdminDashboard>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}) => UseQueryOptions<Awaited<ReturnType<typeof getAdminDashboard>>, TError, TData> & {
    queryKey: QueryKey;
};
export type GetAdminDashboardQueryResult = NonNullable<Awaited<ReturnType<typeof getAdminDashboard>>>;
export type GetAdminDashboardQueryError = ErrorType<unknown>;
/**
 * @summary Read live shop totals and recent purchases
 */
export declare function useGetAdminDashboard<TData = Awaited<ReturnType<typeof getAdminDashboard>>, TError = ErrorType<unknown>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getAdminDashboard>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}): UseQueryResult<TData, TError> & {
    queryKey: QueryKey;
};
export declare const getGetAdminProductsUrl: (params?: GetAdminProductsParams) => string;
/**
 * @summary List products
 */
export declare const getAdminProducts: (params?: GetAdminProductsParams, options?: Parameters<typeof customFetch>[1]) => Promise<ShopProduct[]>;
export declare const getGetAdminProductsQueryKey: (params?: GetAdminProductsParams) => readonly ["/api/admin/products", ...GetAdminProductsParams[]];
export declare const getGetAdminProductsQueryOptions: <TData = Awaited<ReturnType<typeof getAdminProducts>>, TError = ErrorType<unknown>>(params?: GetAdminProductsParams, options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getAdminProducts>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}) => UseQueryOptions<Awaited<ReturnType<typeof getAdminProducts>>, TError, TData> & {
    queryKey: QueryKey;
};
export type GetAdminProductsQueryResult = NonNullable<Awaited<ReturnType<typeof getAdminProducts>>>;
export type GetAdminProductsQueryError = ErrorType<unknown>;
/**
 * @summary List products
 */
export declare function useGetAdminProducts<TData = Awaited<ReturnType<typeof getAdminProducts>>, TError = ErrorType<unknown>>(params?: GetAdminProductsParams, options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getAdminProducts>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}): UseQueryResult<TData, TError> & {
    queryKey: QueryKey;
};
export declare const getCreateAdminProductUrl: () => string;
/**
 * @summary Create a product
 */
export declare const createAdminProduct: (productInput: ProductInput, options?: Parameters<typeof customFetch>[1]) => Promise<ShopProduct>;
export declare const getCreateAdminProductMutationKey: () => readonly ["createAdminProduct"];
export declare const getCreateAdminProductMutationOptions: <TError = ErrorType<unknown>, TContext = unknown>(options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof createAdminProduct>>, TError, CreateAdminProductMutationVariables, TContext>;
    request?: SecondParameter<typeof customFetch>;
}) => UseMutationOptions<Awaited<ReturnType<typeof createAdminProduct>>, TError, CreateAdminProductMutationVariables, TContext>;
export type CreateAdminProductMutationResult = NonNullable<Awaited<ReturnType<typeof createAdminProduct>>>;
export type CreateAdminProductMutationBody = BodyType<ProductInput>;
export type CreateAdminProductMutationError = ErrorType<unknown>;
export type CreateAdminProductMutationVariables = {
    data: BodyType<ProductInput>;
};
/**
* @summary Create a product
*/
export declare const useCreateAdminProduct: <TError = ErrorType<unknown>, TContext = unknown>(options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof createAdminProduct>>, TError, CreateAdminProductMutationVariables, TContext>;
    request?: SecondParameter<typeof customFetch>;
}) => UseMutationResult<Awaited<ReturnType<typeof createAdminProduct>>, TError, CreateAdminProductMutationVariables, TContext>;
export declare const getUpdateAdminProductUrl: (productId: number) => string;
/**
 * @summary Update a product
 */
export declare const updateAdminProduct: (productId: number, productUpdate: ProductUpdate, options?: Parameters<typeof customFetch>[1]) => Promise<ShopProduct>;
export declare const getUpdateAdminProductMutationKey: () => readonly ["updateAdminProduct"];
export declare const getUpdateAdminProductMutationOptions: <TError = ErrorType<unknown>, TContext = unknown>(options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof updateAdminProduct>>, TError, UpdateAdminProductMutationVariables, TContext>;
    request?: SecondParameter<typeof customFetch>;
}) => UseMutationOptions<Awaited<ReturnType<typeof updateAdminProduct>>, TError, UpdateAdminProductMutationVariables, TContext>;
export type UpdateAdminProductMutationResult = NonNullable<Awaited<ReturnType<typeof updateAdminProduct>>>;
export type UpdateAdminProductMutationBody = BodyType<ProductUpdate>;
export type UpdateAdminProductMutationError = ErrorType<unknown>;
export type UpdateAdminProductMutationVariables = {
    productId: number;
    data: BodyType<ProductUpdate>;
};
/**
* @summary Update a product
*/
export declare const useUpdateAdminProduct: <TError = ErrorType<unknown>, TContext = unknown>(options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof updateAdminProduct>>, TError, UpdateAdminProductMutationVariables, TContext>;
    request?: SecondParameter<typeof customFetch>;
}) => UseMutationResult<Awaited<ReturnType<typeof updateAdminProduct>>, TError, UpdateAdminProductMutationVariables, TContext>;
export declare const getDeleteAdminProductUrl: (productId: number) => string;
/**
 * @summary Delete a product
 */
export declare const deleteAdminProduct: (productId: number, options?: Parameters<typeof customFetch>[1]) => Promise<void>;
export declare const getDeleteAdminProductMutationKey: () => readonly ["deleteAdminProduct"];
export declare const getDeleteAdminProductMutationOptions: <TError = ErrorType<unknown>, TContext = unknown>(options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof deleteAdminProduct>>, TError, DeleteAdminProductMutationVariables, TContext>;
    request?: SecondParameter<typeof customFetch>;
}) => UseMutationOptions<Awaited<ReturnType<typeof deleteAdminProduct>>, TError, DeleteAdminProductMutationVariables, TContext>;
export type DeleteAdminProductMutationResult = NonNullable<Awaited<ReturnType<typeof deleteAdminProduct>>>;
export type DeleteAdminProductMutationError = ErrorType<unknown>;
export type DeleteAdminProductMutationVariables = {
    productId: number;
};
/**
* @summary Delete a product
*/
export declare const useDeleteAdminProduct: <TError = ErrorType<unknown>, TContext = unknown>(options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof deleteAdminProduct>>, TError, DeleteAdminProductMutationVariables, TContext>;
    request?: SecondParameter<typeof customFetch>;
}) => UseMutationResult<Awaited<ReturnType<typeof deleteAdminProduct>>, TError, DeleteAdminProductMutationVariables, TContext>;
export declare const getGetAdminGroupsUrl: () => string;
/**
 * @summary List product groups
 */
export declare const getAdminGroups: (options?: Parameters<typeof customFetch>[1]) => Promise<ProductGroup[]>;
export declare const getGetAdminGroupsQueryKey: () => readonly ["/api/admin/groups"];
export declare const getGetAdminGroupsQueryOptions: <TData = Awaited<ReturnType<typeof getAdminGroups>>, TError = ErrorType<unknown>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getAdminGroups>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}) => UseQueryOptions<Awaited<ReturnType<typeof getAdminGroups>>, TError, TData> & {
    queryKey: QueryKey;
};
export type GetAdminGroupsQueryResult = NonNullable<Awaited<ReturnType<typeof getAdminGroups>>>;
export type GetAdminGroupsQueryError = ErrorType<unknown>;
/**
 * @summary List product groups
 */
export declare function useGetAdminGroups<TData = Awaited<ReturnType<typeof getAdminGroups>>, TError = ErrorType<unknown>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getAdminGroups>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}): UseQueryResult<TData, TError> & {
    queryKey: QueryKey;
};
export declare const getCreateAdminGroupUrl: () => string;
/**
 * @summary Create a product group
 */
export declare const createAdminGroup: (productGroupInput: ProductGroupInput, options?: Parameters<typeof customFetch>[1]) => Promise<ProductGroup>;
export declare const getCreateAdminGroupMutationKey: () => readonly ["createAdminGroup"];
export declare const getCreateAdminGroupMutationOptions: <TError = ErrorType<unknown>, TContext = unknown>(options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof createAdminGroup>>, TError, CreateAdminGroupMutationVariables, TContext>;
    request?: SecondParameter<typeof customFetch>;
}) => UseMutationOptions<Awaited<ReturnType<typeof createAdminGroup>>, TError, CreateAdminGroupMutationVariables, TContext>;
export type CreateAdminGroupMutationResult = NonNullable<Awaited<ReturnType<typeof createAdminGroup>>>;
export type CreateAdminGroupMutationBody = BodyType<ProductGroupInput>;
export type CreateAdminGroupMutationError = ErrorType<unknown>;
export type CreateAdminGroupMutationVariables = {
    data: BodyType<ProductGroupInput>;
};
/**
* @summary Create a product group
*/
export declare const useCreateAdminGroup: <TError = ErrorType<unknown>, TContext = unknown>(options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof createAdminGroup>>, TError, CreateAdminGroupMutationVariables, TContext>;
    request?: SecondParameter<typeof customFetch>;
}) => UseMutationResult<Awaited<ReturnType<typeof createAdminGroup>>, TError, CreateAdminGroupMutationVariables, TContext>;
export declare const getUpdateAdminGroupUrl: (groupId: number) => string;
/**
 * @summary Update a product group
 */
export declare const updateAdminGroup: (groupId: number, productGroupUpdate: ProductGroupUpdate, options?: Parameters<typeof customFetch>[1]) => Promise<ProductGroup>;
export declare const getUpdateAdminGroupMutationKey: () => readonly ["updateAdminGroup"];
export declare const getUpdateAdminGroupMutationOptions: <TError = ErrorType<unknown>, TContext = unknown>(options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof updateAdminGroup>>, TError, UpdateAdminGroupMutationVariables, TContext>;
    request?: SecondParameter<typeof customFetch>;
}) => UseMutationOptions<Awaited<ReturnType<typeof updateAdminGroup>>, TError, UpdateAdminGroupMutationVariables, TContext>;
export type UpdateAdminGroupMutationResult = NonNullable<Awaited<ReturnType<typeof updateAdminGroup>>>;
export type UpdateAdminGroupMutationBody = BodyType<ProductGroupUpdate>;
export type UpdateAdminGroupMutationError = ErrorType<unknown>;
export type UpdateAdminGroupMutationVariables = {
    groupId: number;
    data: BodyType<ProductGroupUpdate>;
};
/**
* @summary Update a product group
*/
export declare const useUpdateAdminGroup: <TError = ErrorType<unknown>, TContext = unknown>(options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof updateAdminGroup>>, TError, UpdateAdminGroupMutationVariables, TContext>;
    request?: SecondParameter<typeof customFetch>;
}) => UseMutationResult<Awaited<ReturnType<typeof updateAdminGroup>>, TError, UpdateAdminGroupMutationVariables, TContext>;
export declare const getDeleteAdminGroupUrl: (groupId: number) => string;
/**
 * @summary Delete a product group
 */
export declare const deleteAdminGroup: (groupId: number, options?: Parameters<typeof customFetch>[1]) => Promise<void>;
export declare const getDeleteAdminGroupMutationKey: () => readonly ["deleteAdminGroup"];
export declare const getDeleteAdminGroupMutationOptions: <TError = ErrorType<unknown>, TContext = unknown>(options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof deleteAdminGroup>>, TError, DeleteAdminGroupMutationVariables, TContext>;
    request?: SecondParameter<typeof customFetch>;
}) => UseMutationOptions<Awaited<ReturnType<typeof deleteAdminGroup>>, TError, DeleteAdminGroupMutationVariables, TContext>;
export type DeleteAdminGroupMutationResult = NonNullable<Awaited<ReturnType<typeof deleteAdminGroup>>>;
export type DeleteAdminGroupMutationError = ErrorType<unknown>;
export type DeleteAdminGroupMutationVariables = {
    groupId: number;
};
/**
* @summary Delete a product group
*/
export declare const useDeleteAdminGroup: <TError = ErrorType<unknown>, TContext = unknown>(options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof deleteAdminGroup>>, TError, DeleteAdminGroupMutationVariables, TContext>;
    request?: SecondParameter<typeof customFetch>;
}) => UseMutationResult<Awaited<ReturnType<typeof deleteAdminGroup>>, TError, DeleteAdminGroupMutationVariables, TContext>;
export declare const getGetAdminUsersUrl: (params?: GetAdminUsersParams) => string;
/**
 * @summary Search Telegram customers
 */
export declare const getAdminUsers: (params?: GetAdminUsersParams, options?: Parameters<typeof customFetch>[1]) => Promise<ShopCustomer[]>;
export declare const getGetAdminUsersQueryKey: (params?: GetAdminUsersParams) => readonly ["/api/admin/users", ...GetAdminUsersParams[]];
export declare const getGetAdminUsersQueryOptions: <TData = Awaited<ReturnType<typeof getAdminUsers>>, TError = ErrorType<unknown>>(params?: GetAdminUsersParams, options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getAdminUsers>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}) => UseQueryOptions<Awaited<ReturnType<typeof getAdminUsers>>, TError, TData> & {
    queryKey: QueryKey;
};
export type GetAdminUsersQueryResult = NonNullable<Awaited<ReturnType<typeof getAdminUsers>>>;
export type GetAdminUsersQueryError = ErrorType<unknown>;
/**
 * @summary Search Telegram customers
 */
export declare function useGetAdminUsers<TData = Awaited<ReturnType<typeof getAdminUsers>>, TError = ErrorType<unknown>>(params?: GetAdminUsersParams, options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getAdminUsers>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}): UseQueryResult<TData, TError> & {
    queryKey: QueryKey;
};
export declare const getAdjustAdminUserBalanceUrl: (userId: number) => string;
/**
 * @summary Add or deduct a customer's shop balance
 */
export declare const adjustAdminUserBalance: (userId: number, balanceAdjustment: BalanceAdjustment, options?: Parameters<typeof customFetch>[1]) => Promise<BalanceResult>;
export declare const getAdjustAdminUserBalanceMutationKey: () => readonly ["adjustAdminUserBalance"];
export declare const getAdjustAdminUserBalanceMutationOptions: <TError = ErrorType<unknown>, TContext = unknown>(options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof adjustAdminUserBalance>>, TError, AdjustAdminUserBalanceMutationVariables, TContext>;
    request?: SecondParameter<typeof customFetch>;
}) => UseMutationOptions<Awaited<ReturnType<typeof adjustAdminUserBalance>>, TError, AdjustAdminUserBalanceMutationVariables, TContext>;
export type AdjustAdminUserBalanceMutationResult = NonNullable<Awaited<ReturnType<typeof adjustAdminUserBalance>>>;
export type AdjustAdminUserBalanceMutationBody = BodyType<BalanceAdjustment>;
export type AdjustAdminUserBalanceMutationError = ErrorType<unknown>;
export type AdjustAdminUserBalanceMutationVariables = {
    userId: number;
    data: BodyType<BalanceAdjustment>;
};
/**
* @summary Add or deduct a customer's shop balance
*/
export declare const useAdjustAdminUserBalance: <TError = ErrorType<unknown>, TContext = unknown>(options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof adjustAdminUserBalance>>, TError, AdjustAdminUserBalanceMutationVariables, TContext>;
    request?: SecondParameter<typeof customFetch>;
}) => UseMutationResult<Awaited<ReturnType<typeof adjustAdminUserBalance>>, TError, AdjustAdminUserBalanceMutationVariables, TContext>;
export declare const getGetAdminPurchasesUrl: (params?: GetAdminPurchasesParams) => string;
/**
 * @summary List completed purchases
 */
export declare const getAdminPurchases: (params?: GetAdminPurchasesParams, options?: Parameters<typeof customFetch>[1]) => Promise<ShopPurchase[]>;
export declare const getGetAdminPurchasesQueryKey: (params?: GetAdminPurchasesParams) => readonly ["/api/admin/purchases", ...GetAdminPurchasesParams[]];
export declare const getGetAdminPurchasesQueryOptions: <TData = Awaited<ReturnType<typeof getAdminPurchases>>, TError = ErrorType<unknown>>(params?: GetAdminPurchasesParams, options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getAdminPurchases>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}) => UseQueryOptions<Awaited<ReturnType<typeof getAdminPurchases>>, TError, TData> & {
    queryKey: QueryKey;
};
export type GetAdminPurchasesQueryResult = NonNullable<Awaited<ReturnType<typeof getAdminPurchases>>>;
export type GetAdminPurchasesQueryError = ErrorType<unknown>;
/**
 * @summary List completed purchases
 */
export declare function useGetAdminPurchases<TData = Awaited<ReturnType<typeof getAdminPurchases>>, TError = ErrorType<unknown>>(params?: GetAdminPurchasesParams, options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getAdminPurchases>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}): UseQueryResult<TData, TError> & {
    queryKey: QueryKey;
};
export declare const getGetAdminPromoCodesUrl: () => string;
/**
 * @summary List promo codes
 */
export declare const getAdminPromoCodes: (options?: Parameters<typeof customFetch>[1]) => Promise<PromoCode[]>;
export declare const getGetAdminPromoCodesQueryKey: () => readonly ["/api/admin/promocodes"];
export declare const getGetAdminPromoCodesQueryOptions: <TData = Awaited<ReturnType<typeof getAdminPromoCodes>>, TError = ErrorType<unknown>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getAdminPromoCodes>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}) => UseQueryOptions<Awaited<ReturnType<typeof getAdminPromoCodes>>, TError, TData> & {
    queryKey: QueryKey;
};
export type GetAdminPromoCodesQueryResult = NonNullable<Awaited<ReturnType<typeof getAdminPromoCodes>>>;
export type GetAdminPromoCodesQueryError = ErrorType<unknown>;
/**
 * @summary List promo codes
 */
export declare function useGetAdminPromoCodes<TData = Awaited<ReturnType<typeof getAdminPromoCodes>>, TError = ErrorType<unknown>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getAdminPromoCodes>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}): UseQueryResult<TData, TError> & {
    queryKey: QueryKey;
};
export declare const getCreateAdminPromoCodeUrl: () => string;
/**
 * @summary Create a promo code
 */
export declare const createAdminPromoCode: (promoCodeInput: PromoCodeInput, options?: Parameters<typeof customFetch>[1]) => Promise<PromoCode>;
export declare const getCreateAdminPromoCodeMutationKey: () => readonly ["createAdminPromoCode"];
export declare const getCreateAdminPromoCodeMutationOptions: <TError = ErrorType<unknown>, TContext = unknown>(options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof createAdminPromoCode>>, TError, CreateAdminPromoCodeMutationVariables, TContext>;
    request?: SecondParameter<typeof customFetch>;
}) => UseMutationOptions<Awaited<ReturnType<typeof createAdminPromoCode>>, TError, CreateAdminPromoCodeMutationVariables, TContext>;
export type CreateAdminPromoCodeMutationResult = NonNullable<Awaited<ReturnType<typeof createAdminPromoCode>>>;
export type CreateAdminPromoCodeMutationBody = BodyType<PromoCodeInput>;
export type CreateAdminPromoCodeMutationError = ErrorType<unknown>;
export type CreateAdminPromoCodeMutationVariables = {
    data: BodyType<PromoCodeInput>;
};
/**
* @summary Create a promo code
*/
export declare const useCreateAdminPromoCode: <TError = ErrorType<unknown>, TContext = unknown>(options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof createAdminPromoCode>>, TError, CreateAdminPromoCodeMutationVariables, TContext>;
    request?: SecondParameter<typeof customFetch>;
}) => UseMutationResult<Awaited<ReturnType<typeof createAdminPromoCode>>, TError, CreateAdminPromoCodeMutationVariables, TContext>;
export declare const getDeleteAdminPromoCodeUrl: (code: string) => string;
/**
 * @summary Delete a promo code
 */
export declare const deleteAdminPromoCode: (code: string, options?: Parameters<typeof customFetch>[1]) => Promise<void>;
export declare const getDeleteAdminPromoCodeMutationKey: () => readonly ["deleteAdminPromoCode"];
export declare const getDeleteAdminPromoCodeMutationOptions: <TError = ErrorType<unknown>, TContext = unknown>(options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof deleteAdminPromoCode>>, TError, DeleteAdminPromoCodeMutationVariables, TContext>;
    request?: SecondParameter<typeof customFetch>;
}) => UseMutationOptions<Awaited<ReturnType<typeof deleteAdminPromoCode>>, TError, DeleteAdminPromoCodeMutationVariables, TContext>;
export type DeleteAdminPromoCodeMutationResult = NonNullable<Awaited<ReturnType<typeof deleteAdminPromoCode>>>;
export type DeleteAdminPromoCodeMutationError = ErrorType<unknown>;
export type DeleteAdminPromoCodeMutationVariables = {
    code: string;
};
/**
* @summary Delete a promo code
*/
export declare const useDeleteAdminPromoCode: <TError = ErrorType<unknown>, TContext = unknown>(options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof deleteAdminPromoCode>>, TError, DeleteAdminPromoCodeMutationVariables, TContext>;
    request?: SecondParameter<typeof customFetch>;
}) => UseMutationResult<Awaited<ReturnType<typeof deleteAdminPromoCode>>, TError, DeleteAdminPromoCodeMutationVariables, TContext>;
export declare const getGetAdminSettingsUrl: () => string;
/**
 * @summary Read editable shop settings
 */
export declare const getAdminSettings: (options?: Parameters<typeof customFetch>[1]) => Promise<ShopSettings>;
export declare const getGetAdminSettingsQueryKey: () => readonly ["/api/admin/settings"];
export declare const getGetAdminSettingsQueryOptions: <TData = Awaited<ReturnType<typeof getAdminSettings>>, TError = ErrorType<unknown>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getAdminSettings>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}) => UseQueryOptions<Awaited<ReturnType<typeof getAdminSettings>>, TError, TData> & {
    queryKey: QueryKey;
};
export type GetAdminSettingsQueryResult = NonNullable<Awaited<ReturnType<typeof getAdminSettings>>>;
export type GetAdminSettingsQueryError = ErrorType<unknown>;
/**
 * @summary Read editable shop settings
 */
export declare function useGetAdminSettings<TData = Awaited<ReturnType<typeof getAdminSettings>>, TError = ErrorType<unknown>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof getAdminSettings>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}): UseQueryResult<TData, TError> & {
    queryKey: QueryKey;
};
export declare const getUpdateAdminSettingsUrl: () => string;
/**
 * @summary Update editable shop settings
 */
export declare const updateAdminSettings: (shopSettingsUpdate: ShopSettingsUpdate, options?: Parameters<typeof customFetch>[1]) => Promise<ShopSettings>;
export declare const getUpdateAdminSettingsMutationKey: () => readonly ["updateAdminSettings"];
export declare const getUpdateAdminSettingsMutationOptions: <TError = ErrorType<unknown>, TContext = unknown>(options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof updateAdminSettings>>, TError, UpdateAdminSettingsMutationVariables, TContext>;
    request?: SecondParameter<typeof customFetch>;
}) => UseMutationOptions<Awaited<ReturnType<typeof updateAdminSettings>>, TError, UpdateAdminSettingsMutationVariables, TContext>;
export type UpdateAdminSettingsMutationResult = NonNullable<Awaited<ReturnType<typeof updateAdminSettings>>>;
export type UpdateAdminSettingsMutationBody = BodyType<ShopSettingsUpdate>;
export type UpdateAdminSettingsMutationError = ErrorType<unknown>;
export type UpdateAdminSettingsMutationVariables = {
    data: BodyType<ShopSettingsUpdate>;
};
/**
* @summary Update editable shop settings
*/
export declare const useUpdateAdminSettings: <TError = ErrorType<unknown>, TContext = unknown>(options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof updateAdminSettings>>, TError, UpdateAdminSettingsMutationVariables, TContext>;
    request?: SecondParameter<typeof customFetch>;
}) => UseMutationResult<Awaited<ReturnType<typeof updateAdminSettings>>, TError, UpdateAdminSettingsMutationVariables, TContext>;
export {};
//# sourceMappingURL=api.d.ts.map