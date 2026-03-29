import { expect, test } from '@playwright/test'

async function login(page, username, password) {
  await page.goto('/login')
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
}

test('guest submits quote-confirmed order through browser workflow', async ({ page }) => {
  await login(page, 'guest@seabreeze.local', 'Harbor#2026!')
  await expect(page).toHaveURL(/\/workspace$/)
  await expect(page.getByText('Build cart and request quote')).toBeVisible()

  await page.getByRole('button', { name: 'Add item to cart' }).click()
  await expect(page.getByText('Qty 1')).toBeVisible()

  await page.getByRole('button', { name: 'Confirm quote for cart' }).click()
  await expect(page.getByText('Confirm quoted totals before submit')).toBeVisible()

  await page.getByRole('button', { name: 'Submit confirmed order' }).click()
  await expect(page.getByText('Order created and posted to the selected folio.')).toBeVisible()
})

test('front desk can post reversal and queue folio print', async ({ page }) => {
  await login(page, 'desk@seabreeze.local', 'Harbor#2026!')
  await expect(page).toHaveURL(/\/workspace$/)

  await page.getByRole('button', { name: /Post reversal/i }).click()
  await expect(page.getByText('Reversal posted.')).toBeVisible()

  await page.getByRole('button', { name: /^Queue print$/i }).click()
  await expect(page.getByText(/Print job .* queued at /)).toBeVisible()
})
