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

test('legacy reader can explicitly restart with reference comparison',async({page})=>{
 await page.route('**/api/books',r=>r.fulfill({json:[]}));
 await page.route('**/api/auth/me',r=>r.fulfill({json:{id:'test',name:'测试',role:'student',must_change_password:false}}));
 await page.route('**/api/me/history',r=>r.fulfill({json:[]}));await page.route('**/api/me/stats',r=>r.fulfill({json:{checkins:[]}}));
 await page.route('**/api/speech/status',r=>r.fulfill({json:{configured:true,provider:'reference_similarity'}}));
 const data={book_id:'book',current_page:1,completed_pages:[],pending_jobs:{},latest_results:{},version:{title:'Legacy round',pages:[{id:'p',position:1,kind:'practice',text:'Read',audio_id:null}]}};
 await page.route('**/api/sessions/old',r=>r.fulfill({json:{...data,id:'old',scoring_mode:null,required_page_ids:null}}));
 await page.route('**/api/sessions/new',r=>r.fulfill({json:{...data,id:'new',scoring_mode:'reference_similarity',required_page_ids:[]}}));
 await page.route('**/api/sessions',r=>{expect(r.request().postDataJSON()).toEqual({book_id:'book',restart:true});return r.fulfill({json:{id:'new'}});});
 await page.goto('/#/read/old');await page.getByRole('button',{name:'使用原音比对新开一轮'}).click();
 await expect(page).toHaveURL(/#\/read\/new$/);
 await expect(page.getByRole('button',{name:'开始跟读'})).toHaveCount(0);
 await expect(page.getByText('本页仅阅读',{exact:true})).toBeVisible();
});

test('administrator comparison playback controls stay inside the result card',async({page})=>{
 await page.route('**/api/auth/me',r=>r.fulfill({json:{id:'admin',name:'管理员',role:'admin',must_change_password:false}}));
 const version={id:'v',title:'Layout test',number:1,published:false,pages:[{id:'p',position:1,kind:'practice',text:'Read this.',audio_id:'ref',audio_start_ms:0,audio_end_ms:2000}]};
 const book={id:'layout-test',status:'draft',draft:version,published:null};
 await page.route('**/api/admin/books',r=>r.fulfill({json:[book]}));await page.route('**/api/admin/books/layout-test',r=>r.fulfill({json:book}));
 await page.route('**/api/admin/versions/v/assets',r=>r.fulfill({json:[]}));
 await page.route('**/api/speech/status',r=>r.fulfill({json:{configured:true,provider:'reference_similarity'}}));
 await page.route('**/api/admin/speech/test',r=>r.fulfill({json:{id:'layout-job'}}));
 await page.route('**/api/jobs/layout-job',r=>r.fulfill({json:{id:'layout-job',status:'succeeded',result:{mode:'reference_similarity',overall_score:100,words:[],experimental:true,segments:[{reference_start:0,reference_end:2,recording_start:0,recording_end:2,similarity:100}]}}}));
 await page.goto('/#/admin/book/layout-test');await page.getByRole('button',{name:'试读评分',exact:true}).click();
 const dialog=page.getByRole('dialog',{name:'本页试读评分 · 可选'});
 await dialog.locator('input[type=file]').setInputFiles({name:'layout-fixture.wav',mimeType:'audio/wav',buffer:Buffer.from('ui-only')});
 await dialog.getByRole('button',{name:'运行评分',exact:true}).click();
 const button=dialog.getByRole('button',{name:'听我的对应录音'});await expect(button).toBeVisible();
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});
  await expect.poll(()=>button.evaluate(el=>el.getBoundingClientRect().right<=el.parentElement!.parentElement!.getBoundingClientRect().right)).toBeTruthy();
 }
});
