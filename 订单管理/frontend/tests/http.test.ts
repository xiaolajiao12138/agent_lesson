import { describe, expect, it } from 'vitest';
import { AxiosHeaders, type AxiosAdapter } from 'axios';
import { VAxios } from '../src/utils/http/axios/Axios';

const adapter: AxiosAdapter = async (config) => ({
  data: { code: 200, message: 'ok', data: { value: 7 } },
  status: 200, statusText: 'OK', headers: new AxiosHeaders(), config,
});

describe('参考 VAxios 的响应转换入口', () => {
  it('调用配置的 transform 解包 data，不让页面反复写 response.data.data', async () => {
    const http = new VAxios({ adapter, transform: {
      transformRequestData: (response) => response.data.data,
    } });
    expect(await http.request({ url: '/test' })).toEqual({ value: 7 });
  });
  it('请求选项传递给 transform，支持按次返回原生响应', async () => {
    const http = new VAxios({ adapter, transform: {
      transformRequestData: (response, options) => options.isReturnNativeResponse ? response : response.data.data,
    } });
    const response = await http.request<{ status: number }>({ url: '/test' }, { isReturnNativeResponse: true });
    expect(response.status).toBe(200);
  });
});
