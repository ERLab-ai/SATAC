import {test,expect} from '@playwright/test';

test('A05 actual release: independent alternatives and masked references',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');
 const release=page.getByLabel('الإصدار المعرفي');
 await expect(release.locator('option[value="a0500000-0000-4000-8000-000000000001"]')).toHaveCount(1);
 await release.selectOption('a0500000-0000-4000-8000-000000000001');
 await page.getByLabel('البحث عن موضع أو اسم').fill('شخصية اختبار التعارض');
 await page.getByRole('button',{name:'بحث',exact:true}).click();
 await page.getByRole('region',{name:'نتائج البحث'}).getByRole('button',{name:/شخصية اختبار التعارض/}).click();
 const panel=page.getByTestId('scientific-conflicts');
 await expect(panel.getByRole('heading',{name:'الروايات العلمية المتعارضة'})).toBeVisible();
 const alternatives=panel.getByTestId('conflict-alternative');
 await expect(alternatives).toHaveCount(2);
 await expect(alternatives.nth(0)).toContainText('الموضع التجريبي الأول');
 await expect(alternatives.nth(0)).toContainText('مصدر اختبار أول');
 await expect(alternatives.nth(0)).toContainText('p. 11');
 await expect(alternatives.nth(1)).toContainText('الموضع التجريبي الثاني');
 await expect(alternatives.nth(1)).toContainText('مصدر اختبار ثان');
 await expect(alternatives.nth(1)).toContainText('p. 22');
 await expect(panel).not.toContainText('مصدر محجوب');
 await expect(panel).not.toContainText('رواية محجوبة');
 await page.screenshot({path:'test-results/scientific-conflicts.png'});
 expect(errors).toEqual([]);
});
