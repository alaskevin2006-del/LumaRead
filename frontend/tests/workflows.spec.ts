import {test,expect} from '@playwright/test';
test('administrator manages a resource and temporary student account',async({page})=>{
 await page.goto('/');await page.getByLabel('账号',{exact:true}).fill(process.env.E2E_ADMIN||'admin');await page.getByLabel('密码',{exact:true}).fill(process.env.E2E_PASSWORD||'AdminPass123');await page.getByRole('button',{name:'登录，开始阅读'}).click();
 await expect(page.getByRole('heading',{name:'教学资源',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'新建绘本'}).click();await page.getByLabel('绘本标题').fill('Browser Test Story');await page.getByRole('button',{name:'创建草稿'}).click();await expect(page.getByRole('heading',{name:'Browser Test Story'})).toBeVisible();
 await page.getByRole('button',{name:'新增页面'}).click();await expect(page.getByLabel('标准英文文本')).toBeVisible();await page.getByLabel('标准英文文本').fill('The dog sees a ball.');await page.getByRole('button',{name:'保存本页'}).click();await expect(page.getByText('本页已保存',{exact:true})).toBeVisible();await page.screenshot({path:'../.local/admin-editor.png',fullPage:true});
 await page.getByRole('button',{name:'发布检查'}).click();await expect(page.getByText(/请设置封面/)).toBeVisible();await page.getByRole('button',{name:'返回编辑'}).click();
 await page.getByRole('button',{name:'学生账号',exact:true}).click();await page.getByRole('button',{name:'创建学生账号'}).click();await page.getByLabel('显示名称').fill('浏览器测试学生');await page.getByLabel('登录账号').fill('browser_'+Date.now());await page.getByRole('button',{name:'创建账号',exact:true}).click();await expect(page.getByText('临时密码',{exact:true})).toBeVisible();
});
test('mobile login has visible controls without horizontal overflow',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/');await expect(page.getByRole('button',{name:'登录，开始阅读'})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});

test('student changes temporary password, reads published content and resumes without fabricated scores',async({page,request})=>{
 const headers={'X-LumaRead':'1'};
 expect((await request.post('/api/auth/login',{headers,data:{username:process.env.E2E_ADMIN||'admin',password:process.env.E2E_PASSWORD||'AdminPass123'}})).ok()).toBeTruthy();
 const username='reader_'+Date.now();
 expect((await request.post('/api/admin/users',{headers,data:{username,name:'阅读测试',password:'Student123'}})).ok()).toBeTruthy();
 const book=await (await request.post('/api/admin/books',{headers,data:{title:'E2E Reading Story',level:'A'}})).json();const vid=book.draft.id;
 const p=await (await request.post(`/api/admin/versions/${vid}/pages`,{headers})).json();
 const fs=await import('node:fs');
 const image=await (await request.post(`/api/admin/versions/${vid}/assets`,{headers,multipart:{kind:'image',file:{name:'cover.png',mimeType:'image/png',buffer:fs.readFileSync('public/sample-book.png')}}})).json();
 const wav=Buffer.alloc(32044);wav.write('RIFF');wav.writeUInt32LE(32036,4);wav.write('WAVEfmt ',8);wav.writeUInt32LE(16,16);wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);wav.writeUInt32LE(16000,24);wav.writeUInt32LE(32000,28);wav.writeUInt16LE(2,32);wav.writeUInt16LE(16,34);wav.write('data',36);wav.writeUInt32LE(32000,40);
 const audio=await (await request.post(`/api/admin/versions/${vid}/assets`,{headers,multipart:{kind:'audio',file:{name:'test-only-silence.wav',mimeType:'audio/wav',buffer:wav}}})).json();
 expect((await request.patch(`/api/admin/versions/${vid}`,{headers,data:{title:'E2E Reading Story',level:'A',cover_id:image.id}})).ok()).toBeTruthy();
 expect((await request.patch(`/api/admin/pages/${p.id}`,{headers,data:{kind:'practice',text:'The dog sees a ball.',image_id:image.id,audio_id:audio.id,audio_start_ms:0,audio_end_ms:1000,reviewed:true}})).ok()).toBeTruthy();
 expect((await request.post(`/api/admin/versions/${vid}/publish`,{headers})).ok()).toBeTruthy();
 await page.setViewportSize({width:390,height:844});await page.goto('/');await page.getByLabel('账号',{exact:true}).fill(username);await page.getByLabel('密码',{exact:true}).fill('Student123');await page.getByRole('button',{name:'登录，开始阅读'}).click();
 await expect(page.getByRole('heading',{name:'设置自己的密码'})).toBeVisible();
 await page.getByLabel('当前密码').fill('Student123');await page.getByLabel('新密码',{exact:true}).fill('Student456');await page.getByLabel('确认新密码').fill('Student456');await page.getByRole('button',{name:'保存密码'}).click();
 await page.getByRole('button',{name:'绘本',exact:true}).click();await page.getByLabel('搜索绘本').fill('E2E Reading Story');await page.getByRole('button',{name:/E2E Reading Story/}).last().click();await page.getByRole('button',{name:'开始阅读',exact:true}).click();
 await expect(page.getByText('The dog sees a ball.',{exact:true})).toBeVisible();await page.getByRole('button',{name:'听原音',exact:true}).click();await expect(page.getByRole('button',{name:'暂停原音'})).toBeVisible();await page.getByRole('button',{name:'暂停原音'}).click();
 await expect(page.getByRole('button',{name:'开始跟读'})).toBeVisible();await page.getByRole('button',{name:'开始跟读'}).click();await expect(page.getByText(/真实评分服务尚未配置/)).toBeVisible();
 await page.getByRole('button',{name:'完成本书'}).click();await expect(page.getByRole('dialog',{name:'还有几页需要跟读'})).toBeVisible();await page.getByRole('button',{name:'去第 1 页'}).click();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
 await page.screenshot({path:'../.local/student-reader.png',fullPage:true});await page.getByRole('button',{name:'退出阅读'}).click();await page.getByRole('button',{name:/继续上次阅读/}).click();await expect(page.getByText('The dog sees a ball.',{exact:true})).toBeVisible();
});

test('a pending microphone request is cancelled when the reader changes page',async({page})=>{
 await page.route('**/api/auth/me',r=>r.fulfill({json:{id:'test',username:'test',name:'测试',role:'student',must_change_password:false}}));
 await page.route('**/api/books',r=>r.fulfill({json:[]}));await page.route('**/api/me/history',r=>r.fulfill({json:[]}));await page.route('**/api/me/stats',r=>r.fulfill({json:{checkins:[]}}));await page.route('**/api/speech/status',r=>r.fulfill({json:{configured:true}}));
 const pages=[1,2].map(n=>({id:'page'+n,position:n,kind:'practice',text:'Page '+n,image_id:null,audio_id:null,audio_start_ms:0,audio_end_ms:null,reviewed:true}));
 await page.route('**/api/sessions/permission-test',r=>r.fulfill({json:{id:'permission-test',current_page:1,completed_pages:[],pending_jobs:{},latest_results:{},version:{title:'Permission Test',level:'A',pages}}}));await page.route('**/api/sessions/permission-test/progress',r=>r.fulfill({json:{ok:true}}));
 await page.addInitScript(()=>{
  localStorage.setItem('luma-recording-consent','1');
  const testWindow=window as any;
  navigator.mediaDevices.getUserMedia=()=>new Promise(resolve=>{testWindow.grantMic=()=>{const ctx=new AudioContext(),destination=ctx.createMediaStreamDestination();testWindow.micStream=destination.stream;resolve(destination.stream);};});
 });
 await page.goto('/#/read/permission-test');await page.getByRole('button',{name:'开始跟读'}).click();await page.getByRole('button',{name:'下一页'}).click();
 await page.evaluate(()=>(window as any).grantMic());
 await expect(page.getByText('Page 2',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'开始跟读'})).toBeEnabled();await expect(page.getByRole('button',{name:'读完了'})).toHaveCount(0);
 await expect.poll(()=>page.evaluate(()=>(window as any).micStream.getTracks().every((t:MediaStreamTrack)=>t.readyState==='ended'))).toBe(true);
});

test('admin bulk import and book-level audio mapping keep operations together',async({page,request})=>{
 const headers={'X-LumaRead':'1'};
 await page.goto('/');await page.getByLabel('账号',{exact:true}).fill('admin');await page.getByLabel('密码',{exact:true}).fill('AdminPass123');await page.getByRole('button',{name:'登录，开始阅读'}).click();
 await expect(page.getByRole('button',{name:'评分测试',exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'学生账号',exact:true}).click();await page.getByRole('button',{name:'批量导入',exact:true}).click();
 const suffix=Date.now();await page.getByLabel('或粘贴 Excel 单元格').fill(`姓名\t账号\t班级\n甲\tbulk_a${suffix}\t一班\n乙\tbulk_b${suffix}\t一班`);
 await page.getByRole('button',{name:'确认导入 2 人'}).click();await expect(page.getByText('已生成 2 人的登录信息，请下载保存。')).toBeVisible();await page.getByRole('button',{name:'我已妥善保存'}).click();
 await page.getByLabel('搜索学生').fill('bulk_');await page.getByLabel('全选筛选结果').check();await page.getByRole('button',{name:'调整班级',exact:true}).click();await page.getByLabel('班级名称').fill('批量测试班');await page.getByRole('button',{name:'保存班级',exact:true}).click();await expect(page.getByRole('cell',{name:'批量测试班',exact:true}).first()).toBeVisible();
 await page.getByRole('button',{name:'教学资源',exact:true}).click();await page.getByRole('button',{name:'新建绘本'}).click();await expect(page.getByLabel('等级',{exact:true})).toHaveCount(0);await page.getByLabel('绘本标题').fill('Batch audio '+suffix);await page.getByRole('button',{name:'创建草稿'}).click();await page.getByRole('button',{name:'新增页面',exact:true}).click();
 await page.getByRole('button',{name:'后插一页'}).click();await expect(page.getByRole('heading',{name:'第 2 页内容'})).toBeVisible();
 await page.getByRole('button',{name:'音频管理',exact:true}).click();await page.getByLabel('自动跳过展示页').uncheck();await page.getByRole('button',{name:'批量上传分页音频',exact:true}).click();
 const wav=Buffer.alloc(32044);wav.write('RIFF');wav.writeUInt32LE(32036,4);wav.write('WAVEfmt ',8);wav.writeUInt32LE(16,16);wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);wav.writeUInt32LE(16000,24);wav.writeUInt32LE(32000,28);wav.writeUInt16LE(2,32);wav.writeUInt16LE(16,34);wav.write('data',36);wav.writeUInt32LE(32000,40);
 await page.getByLabel('选择或拖入多个分页音频（按数字排序）').setInputFiles([{name:'10.wav',mimeType:'audio/wav',buffer:wav},{name:'2.wav',mimeType:'audio/wav',buffer:wav}]);
 const dialog=page.getByRole('dialog',{name:'绘本音频管理'});await expect(dialog.locator('tbody tr').first()).toContainText('2.wav');await page.getByRole('button',{name:'一键上传并保存对应关系'}).click();await expect(page.getByText('音频已全部绑定并保存。')).toBeVisible();
 await page.getByRole('button',{name:'上传整本音频',exact:true}).click();await page.getByLabel('选择已上传的整本音频').selectOption({label:'2.wav'});await page.getByLabel('片段 1 开始').fill('0');await page.getByLabel('片段 1 结束').fill('0.5');await page.getByLabel('片段 2 开始').fill('0.5');await page.getByLabel('片段 2 结束').fill('1');await page.getByLabel('允许替换所选页面已有音频').check();await page.getByRole('button',{name:'一键上传并保存对应关系'}).click();await expect(page.getByText('音频已全部绑定并保存。')).toBeVisible();await dialog.getByRole('button',{name:'关闭',exact:true}).click();
 await page.screenshot({path:'../.local/admin-updated.png',fullPage:true});
});

test('student browsing has no level classification',async({page})=>{
 await page.route('**/api/auth/me',r=>r.fulfill({json:{id:'student',username:'student',name:'学生',role:'student',must_change_password:false}}));
 const pages=[{id:'p',position:1,kind:'display',text:'A story.',image_id:null,audio_id:null,audio_start_ms:0,audio_end_ms:null}];
 const version={id:'v',title:'Story without levels',level:'C',description:'',cover_id:null,pages};
 await page.route('**/api/books',r=>r.fulfill({json:[{id:'b',status:'published',published:version}]}));
 await page.route('**/api/me/history',r=>r.fulfill({json:[{id:'s',book_id:'b',title:version.title,level:'C',page_count:0,completed_pages:[],current_page:1,completed_at:null}]}));
 await page.route('**/api/me/stats',r=>r.fulfill({json:{checkins:[],today:'2026-10-19'}}));
 await page.route('**/api/sessions/s',r=>r.fulfill({json:{id:'s',current_page:1,completed_pages:[],pending_jobs:{},latest_results:{},version}}));
 await page.route('**/api/speech/status',r=>r.fulfill({json:{configured:false}}));
 for(const route of ['/','/books','/book/b','/history','/read/s']){
  await page.goto('/#'+route);await expect(page.getByText('Story without levels',{exact:true}).first()).toBeVisible();
  await expect(page.getByText(/Level [ABC]/)).toHaveCount(0);
 }
 await page.goto('/#/books');await page.getByLabel('搜索绘本').fill('not found');await expect(page.getByText('还没找到这个故事')).toBeVisible();
});
