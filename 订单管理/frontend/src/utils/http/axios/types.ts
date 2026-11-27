import type { AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
export interface Result<T = unknown> { code: number; message: string; data: T; request_id?: string }
export interface RequestOptions {
  withToken?: boolean;
  isTransformResponse?: boolean;
  isReturnNativeResponse?: boolean;
  isShowErrorMessage?: boolean;
}
export interface AxiosTransform {
  beforeRequestHook?: (config: AxiosRequestConfig, options: RequestOptions) => AxiosRequestConfig;
  requestInterceptors?: (config: InternalAxiosRequestConfig, options: RequestOptions) => InternalAxiosRequestConfig;
  transformRequestData?: (response: AxiosResponse, options: RequestOptions) => unknown;
  responseInterceptorsCatch?: (error: unknown) => Error;
}
export interface CreateAxiosOptions extends AxiosRequestConfig {
  requestOptions?: RequestOptions;
  transform?: AxiosTransform;
}
