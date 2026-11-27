<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { login } from "../stores/auth";
import { showError } from "../stores/notice";
import Icon from "../components/Icon.vue";
const username = ref(""),
  password = ref(""),
  visible = ref(false),
  busy = ref(false);
const router = useRouter();
async function submit() {
  if (busy.value) return;
  busy.value = true;
  try {
    const user = await login({
      username: username.value,
      password: password.value,
    });
    await router.push(user.role === "admin" ? "/orders" : "/chat");
  } catch (error) {
    showError(error);
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <div class="login-page">
    <section class="login-form-area">
      <div class="login-form-wrap">
        <span class="login-chip"
          ><Icon name="shield" :size="15" />订单服务工作台</span
        >
        <h2>欢迎回来</h2>
        <p class="login-subtitle">登录你的账号，开始今天的工作。</p>
        <form class="login-form" @submit.prevent="submit">
          <label for="username">账号</label>
          <div class="input-with-icon">
            <Icon name="user" :size="19" /><input
              id="username"
              v-model="username"
              name="username"
              autocomplete="username"
              placeholder="请输入账号"
              required
              maxlength="64"
            />
          </div>
          <label for="password">密码</label>
          <div class="input-with-icon">
            <Icon name="lock" :size="19" /><input
              id="password"
              v-model="password"
              name="password"
              :type="visible ? 'text' : 'password'"
              autocomplete="current-password"
              placeholder="请输入密码"
              required
              maxlength="128"
            /><button
              type="button"
              class="icon-button"
              :aria-label="visible ? '隐藏密码' : '显示密码'"
              @click="visible = !visible"
            >
              <Icon name="eye" :size="18" />
            </button>
          </div>
          <div class="login-note">
            <Icon name="shield" :size="14" />登录后，根据账号角色展示对应功能
          </div>
          <button
            type="submit"
            class="button primary login-submit"
            :disabled="busy"
          >
            <span v-if="busy" class="spinner"></span
            >{{ busy ? "正在登录…" : "登录工作台" }}
          </button>
        </form>
        <div class="real-login-tip">
          请使用你在 Python 后端创建的账号登录。
        </div>
      </div>
      <footer class="login-bottom">订单管理 · 让每一次服务有迹可循</footer>
    </section>
  </div>
</template>
