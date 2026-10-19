import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',timeout:45000,use:{baseURL:process.env.E2E_URL||'http://127.0.0.1:3000',trace:'retain-on-failure',launchOptions:process.env.PLAYWRIGHT_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_EXECUTABLE_PATH}:{}},reporter:'list'});
