import {test,expect} from '@playwright/test';

test('reference results show aligned audio segments and no invented word assessment',async({page})=>{
 await page.route('**/api/auth/me',r=>r.fulfill({json:{id:'test',username:'test',name:'测试',role:'student',must_change_password:false}}));
 await page.route('**/api/books',r=>r.fulfill({json:[]}));await page.route('**/api/me/history',r=>r.fulfill({json:[]}));await page.route('**/api/me/stats',r=>r.fulfill({json:{checkins:[]}}));await page.route('**/api/speech/status',r=>r.fulfill({json:{configured:true,provider:'reference_similarity'}}));
 const pages=[1,2].map(n=>({id:'page'+n,position:n,kind:'practice',text:'Page '+n,image_id:null,audio_id:n===1?'ref':null,audio_start_ms:5000,audio_end_ms:7000}));
 const result={mode:'reference_similarity',overall_score:82.3,experimental:true,words:[],reference_audio_id:'ref',reference_offset:5,recording_audio_id:'own',segments:[{reference_start:.2,reference_end:1.5,recording_start:.1,recording_end:1.8,similarity:82.3}]};
 await page.route('**/api/sessions/reference-test',r=>r.fulfill({json:{id:'reference-test',current_page:1,scoring_mode:'reference_similarity',required_page_ids:['page1'],completed_pages:['page1'],pending_jobs:{},latest_results:{page1:result},version:{title:'Reference Test',pages}}}));
 await page.route('**/api/sessions/reference-test/progress',r=>r.fulfill({json:{ok:true}}));
 await page.setViewportSize({width:390,height:844});await page.goto('/#/read/reference-test');
 await expect(page.getByText('原音相似度指数',{exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'听我的对应录音'})).toBeVisible();
 await expect(page.getByText(/不是发音正确率/)).toBeVisible();
 await expect(page.getByText('本页得分',{exact:true})).toHaveCount(0);
 await expect(page.locator('.word-red,.word-green,.word-orange')).toHaveCount(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
 await page.screenshot({path:'../.local/reference-reader.png',fullPage:true});
 await page.getByRole('button',{name:'下一页',exact:true}).click();
 await expect(page.getByText('本页仅阅读',{exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'开始跟读'})).toHaveCount(0);
});
