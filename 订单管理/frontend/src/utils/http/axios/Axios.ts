/** 参考 new_ad_web 的 VAxios：实例、拦截器、transform 和按次请求选项分层。 */
import axios, { type AxiosInstance, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios';
import type { CreateAxiosOptions, RequestOptions } from './types';

type ConfigWithOptions = AxiosRequestConfig & { requestOptions?: RequestOptions };

export class VAxios {
  private instance: AxiosInstance;
  constructor(private options: CreateAxiosOptions) {
    const { transform: _transform, requestOptions: _requestOptions, ...defaults } = options;
    this.instance = axios.create(defaults);
    this.instance.interceptors.request.use((config) => {
      const requestOptions = (config as InternalAxiosRequestConfig & ConfigWithOptions).requestOptions || {};
      return this.options.transform?.requestInterceptors?.(config, requestOptions) || config;
    });
  }
  getAxios(): AxiosInstance { return this.instance; }
  async request<T>(config: AxiosRequestConfig, options?: RequestOptions): Promise<T> {
    const opt = { ...this.options.requestOptions, ...options };
    // 只复制顶层配置，保留 AbortSignal、FormData 等对象原有类型。
    const prepared = this.options.transform?.beforeRequestHook?.({ ...config }, opt) || { ...config };
    try {
      const response = await this.instance.request({ ...prepared, requestOptions: opt } as ConfigWithOptions);
      const hook = this.options.transform?.transformRequestData;
      return (hook ? hook(response, opt) : response.data) as T;
    } catch (error) {
      const normalized = this.options.transform?.responseInterceptorsCatch?.(error) || error;
      if (opt.isShowErrorMessage && typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('app:api-error', { detail: normalized instanceof Error ? normalized.message : '请求失败' }));
      }
      throw normalized;
    }
  }
  get<T>(config: AxiosRequestConfig, options?: RequestOptions) { return this.request<T>({ ...config, method: 'GET' }, options); }
  post<T>(config: AxiosRequestConfig, options?: RequestOptions) { return this.request<T>({ ...config, method: 'POST' }, options); }
  patch<T>(config: AxiosRequestConfig, options?: RequestOptions) { return this.request<T>({ ...config, method: 'PATCH' }, options); }
  delete<T>(config: AxiosRequestConfig, options?: RequestOptions) { return this.request<T>({ ...config, method: 'DELETE' }, options); }
}
