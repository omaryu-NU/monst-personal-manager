import {test,expect} from '@playwright/test';
test('ホーム・図鑑・設定へ移動しバックアップ機能を確認',async({page})=>{
 await page.goto('/');await expect(page.getByText('MONST PERSONAL').first()).toBeVisible();
 await page.getByRole('button',{name:/キャラ図鑑|検索/}).first().click();
 await expect(page.getByText('キャラ図鑑').first()).toBeVisible();
 await page.getByRole('button',{name:'設定',exact:true}).first().click();
 await expect(page.getByText('v1.0 データ診断・安全なバックアップ')).toBeVisible();
 await expect(page.getByRole('button',{name:'JSONをダウンロード'})).toBeEnabled();
});
