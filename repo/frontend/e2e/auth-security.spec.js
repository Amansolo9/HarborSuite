import { expect, test } from '@playwright/test'
import { execSync } from 'node:child_process'
import path from 'node:path'

async function login(page, username, password) {
  await page.goto('/login')
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
}

test('intercepts direct finance URL for unauthenticated user', async ({ page }) => {
  await page.goto('/workspace/finance')
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByText('Start a session')).toBeVisible()
})

test('enforces lockout after repeated invalid sign-in attempts', async ({ request }) => {
  let lastBody = null
  for (let attempt = 0; attempt < 6; attempt += 1) {
    const response = await request.post('http://127.0.0.1:8000/api/v1/auth/login', {
      data: { username: 'editor@seabreeze.local', password: 'WrongPassword!1' },
    })
    lastBody = await response.json()
  }
  const detailMessage = typeof lastBody?.detail === 'object' && lastBody?.detail !== null
    ? String(lastBody.detail.message || '')
    : String(lastBody?.detail || '')
  expect(detailMessage.toLowerCase()).toContain('locked')
})

test('forces idle logout from active session', async ({ page }) => {
  await login(page, 'guest@seabreeze.local', 'Harbor#2026!')
  await expect(page).toHaveURL(/\/workspace$/)
  await expect(page.getByText('HarborSuite Control Deck')).toBeVisible()

  const dbPath = path.resolve(process.cwd(), '..', 'e2e.db')
  const scriptPath = path.resolve(process.cwd(), '..', 'scripts', 'expire_sessions.py')
  execSync(`python "${scriptPath}" "${dbPath}"`)
  await page.reload()

  await expect(page).toHaveURL(/\/login$/)
})
