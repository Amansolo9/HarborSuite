import { createApp } from "vue";
import AppShell from "./AppShell.vue";
import router from "./router";
import './styles/app-shell.css'

createApp(AppShell).use(router).mount("#app");
