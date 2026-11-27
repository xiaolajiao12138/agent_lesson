/** 与参考项目一样，集中创建 http 实例；业务 API 统一 import { http }。 */
import { VAxios } from './Axios';
import { transform } from './axiosTransform';
export const http = new VAxios({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000,
  transform,
  requestOptions: { withToken: true, isTransformResponse: true, isShowErrorMessage: false },
});
export { ApiError } from './axiosTransform';
