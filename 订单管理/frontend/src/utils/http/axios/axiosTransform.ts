/** 公共转换钩子。页面/API 文件不再各自处理 Token、code 和网络错误。 */
import axios from 'axios';
import { clearToken, getToken } from '../../token';
import type { AxiosTransform } from './types';

export class ApiError extends Error {
  constructor(message: string, public code: number, public requestId?: string) { super(message); this.name = 'ApiError'; }
}
export const transform: AxiosTransform = {
  beforeRequestHook(config) {
    // GET 使用 params；写请求推荐使用 data。不自动重试写请求，避免重复提交。
    if (config.params && typeof config.params === 'object') {
      config.params = Object.fromEntries(Object.entries(config.params).filter(([, value]) => value !== undefined));
    }
    return config;
  },
  requestInterceptors(config, options) {
    const token = getToken();
    if (options.withToken !== false && token) config.headers.set('Authorization', `Bearer ${token}`);
    return config;
  },
  transformRequestData(response, options) {
    if (options.isReturnNativeResponse) return response;
    if (options.isTransformResponse === false) return response.data;
    const body = response.data;
    if (!body || typeof body.code !== 'number') throw new ApiError('接口响应不符合 { code, message, data } 约定', 502);
    if (body.code !== 200) throw new ApiError(body.message || '操作失败', body.code, body.request_id);
    return body.data;
  },
  responseInterceptorsCatch(error) {
    if (error instanceof ApiError) return error;
    if (axios.isAxiosError(error)) {
      if (error.response?.status === 401) {
        clearToken();
        if (typeof window !== 'undefined') window.dispatchEvent(new Event('app:unauthorized'));
      }
      const body = error.response?.data;
      const message = body?.message || body?.detail || (error.code === 'ECONNABORTED' ? '请求超时，请稍后重试' : error.response ? '接口请求失败' : '无法连接后端，请检查服务是否启动');
      return new ApiError(typeof message === 'string' ? message : '请求参数校验失败', error.response?.status || 0, body?.request_id);
    }
    return error instanceof Error ? error : new Error('请求失败');
  },
};
