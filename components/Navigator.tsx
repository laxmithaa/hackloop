'use client';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { AlertCircle, ArrowLeft, ArrowRight, Check, CheckCircle2, ChevronDown, CircleHelp, ClipboardList, FileHeart, FileSearch, Globe2, Headphones, HeartHandshake, LockKeyhole, Mic, ShieldCheck, Sparkles, UploadCloud, Volume2, FileText, BookOpen, Info } from 'lucide-react';
import { useApp } from './AppProvider';
import type { Language, TranslationKey } from '@/lib/translations';
import type { ComparisonStatus, IdentificationResult } from '@/lib/api';
import { failureMessage, type ApiFailure } from '@/lib/apiErrors';

const IDENTIFICATION_MESSAGES: Record<IdentificationResult['status'], TranslationKey> = {
 access_code_required:'identifiedFound',
 bill_not_found:'identifyBillMissing',
 bill_number_not_found:'identifyNumberMissing',
 hospital_not_registered:'identifyHospitalMissing',
 unreadable_image:'identifyUnreadable',
 ambiguous_hospital:'identifyAmbiguous',
};
const MANUAL_RECOVERY: IdentificationResult['status'][] = ['bill_not_found','bill_number_not_found','hospital_not_registered','ambiguous_hospital','unreadable_image'];

function comparisonKey(status: ComparisonStatus | null | undefined): TranslationKey {
 switch(status){case 'matched':return 'comparisonMatched';case 'amounts_differ':return 'comparisonDiffer';case 'insufficient_evidence':return 'comparisonInsufficient';default:return 'comparisonNone'}
}
function formatCurrency(value?: string): string | null {
 if(!value)return null;
 const amount=Number(value);
 if(!Number.isFinite(amount))return value;
 return new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',minimumFractionDigits:2,maximumFractionDigits:2}).format(amount);
}
function formatDate(value?: string): string {
 if(!value)return '';
 const date=new Date(`${value}T00:00:00`);
 return Number.isNaN(date.getTime())?value:date.toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'});
}
function formatTimestamp(value?: string): string {
 if(!value)return '';
 const date=new Date(value);
 return Number.isNaN(date.getTime())?value:date.toLocaleString('en-IN',{day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'});
}
function fillTemplate(text:string,values:Record<string,string>):string {
 return text.replace(/\{(\w+)\}/g,(_match:string,key:string)=>values[key]??'');
}
function FailureNotice({title,failure,onRetry}:{title:string;failure:ApiFailure;onRetry?:()=>void}){
 const {t}=useApp();
 return <div className="status-box status-error" role="alert">
  <AlertCircle size={26} aria-hidden="true"/>
  <div>
   <h2>{title}</h2>
   <p>{failureMessage(failure,t)}</p>
   {failure.requestId&&<p className="hint">{t('errorReference')}: {failure.requestId}</p>}
   {onRetry?<div className="actions"><button type="button" className="button secondary" onClick={onRetry}>{t('retry')}</button></div>:<p className="hint">{t('retryHint')}</p>}
  </div>
 </div>;
}

function LanguageSelect(){const {language,setLanguage,t}=useApp();return <label className="language"><Globe2 size={18} aria-hidden="true"/><span className="sr-only">{t('language')}</span><select aria-label={t('language')} value={language} onChange={e=>setLanguage(e.target.value as Language)}><option value="en">English</option><option value="hi">हिन्दी</option><option value="kn">ಕನ್ನಡ</option></select><ChevronDown size={15} aria-hidden="true"/></label>}
function Header(){const {t,restart}=useApp();return <><a className="skip" href="#main">{t('skip')}</a><header className="header"><div className="header-inner"><Link href="/" className="brand" onClick={restart}><span className="brand-icon"><FileHeart size={23}/></span><span className="brand-name">Healthcare Bill <strong>Navigator</strong><small>{t('tagline')}</small></span></Link><nav className="nav" aria-label="Main navigation"><Link href="/">{t('home')}</Link><Link href="/#how-it-works">{t('how')}</Link><Link href="/patient/help">{t('help')}</Link></nav><LanguageSelect/></div></header></>}
function Footer(){const {t}=useApp();return <footer className="footer"><div className="footer-inner"><div><div className="footer-brand"><FileHeart size={19}/> Healthcare Bill Navigator</div><p>{t('footer')}</p></div><div className="footer-links"><Link href="/patient/help">{t('help')}</Link><Link href="/support">{t('support')}</Link></div><p className="footer-note">{t('footerNote')}</p></div></footer>}
function Demo({short=false}:{short?:boolean}){const {t}=useApp();return <div className="demo-notice"><Info size={18} aria-hidden="true"/><span>{t(short?'demoIntro':'demo')}</span></div>}
function ButtonLink({href,children,secondary=false}:{href:string;children:React.ReactNode;secondary?:boolean}){return <Link className={`button ${secondary?'secondary':'primary'}`} href={href}>{children}{!secondary&&<ArrowRight size={18} aria-hidden="true"/>}</Link>}
function PageHeading({title,intro,back='/'}:{title:string;intro:string;back?:string}){const {t}=useApp();return <><Link href={back} className="back-link"><ArrowLeft size={17}/>{t('back')}</Link><div className="page-heading"><span className="eyebrow">{t('demoShort')}</span><h1>{title}</h1><p>{intro}</p></div></>}
function Home(){const {t}=useApp();return <><section className="hero"><div className="container hero-grid"><div className="hero-copy"><div className="eyebrow"><span className="eyebrow-dot"/>{t('eyebrow')}</div><h1>{t('hero')}<br/><em>{t('heroAccent')}</em></h1><p className="hero-intro">{t('intro')}</p><div className="hero-actions"><ButtonLink href="/patient">{t('start')}</ButtonLink><Link className="text-link" href="/patient/help"><Headphones size={19}/>{t('human')}<ArrowRight size={16}/></Link></div><details className="privacy"><summary><ShieldCheck size={21}/> {t('privacyDetails')}</summary><p>{t('privateText')} {t('demoIntro')}</p></details></div><div className="hero-art" aria-hidden="true"><div className="art-circle circle-one"/><div className="art-circle circle-two"/><div className="art-plus plus-one">+</div><div className="art-plus plus-two">+</div><div className="art-card"><div className="art-card-top"><div className="art-hospital"><div className="art-cross">+</div><div><b>SAMPLE HOSPITAL</b><span>BILL SUMMARY</span></div></div><div className="art-dots">•••</div></div><div className="art-line long"/><div className="art-line medium"/><div className="art-divider"/><div className="art-row"><span className="art-square"/><div><div className="art-line medium"/><div className="art-line short"/></div><div className="art-line amount"/></div><div className="art-row"><span className="art-square teal"/><div><div className="art-line medium"/><div className="art-line short"/></div><div className="art-line amount"/></div><div className="art-bottom"><span/><span/></div><div className="art-badge"><Check size={19}/> <span>Easy to understand</span></div></div><div className="floating-icon"><HeartHandshake size={30}/></div><div className="art-caption">A LITTLE MORE CLARITY, A LOT MORE CONFIDENCE</div></div></div></section><div className="notice-strip"><div className="container"><Info size={18}/><span>{t('noAdvice')}</span></div></div><section id="how-it-works" className="how-section container"><div className="section-heading"><span className="eyebrow">{t('how')}</span><h2>{t('howTitle')}</h2><p>{t('howIntro')}</p></div><details><summary>{t('how')}</summary><div className="steps">{([[FileSearch,'step1','step1Text'],[ClipboardList,'step2','step2Text'],[BookOpen,'step3','step3Text']] as const).map(([Icon,title,desc],i)=><article className="step-card" key={title}><div className="step-top"><div className="step-icon"><Icon size={26}/></div><span>0{i+1}</span></div><h3>{t(title)}</h3><p>{t(desc)}</p></article>)}</div></details></section><section className="container help-banner"><div className="help-icon"><HeartHandshake size={30}/></div><div><h2>{t('helpTitle')}</h2><p>{t('helpText')}</p></div><ButtonLink href="/patient/help" secondary>{t('helpButton')} <ArrowRight size={17}/></ButtonLink></section><section className="container home-demo"><Demo short/></section></>}
function Consent(){
 const {t,chooseConsent,consent,consentBusy,consentFailure,sessionId}=useApp();
 return <div className="page narrow">
  <PageHeading title={t('consentTitle')} intro={t('consentIntro')}/>
  <Demo short/>
  <div className="panel consent-panel">
   <details open>
    <summary>{t('consentWhat')}</summary>
    {([['consentWhat','consentWhatText'],['consentWhy','consentWhyText'],['consentUse','consentUseText'],['consentAgree','consentAgreeText']] as const).map(([title,text])=><div className="consent-item" key={title}><span className="check-circle"><Check size={15}/></span><div><h2>{t(title)}</h2><p>{t(text)}</p></div></div>)}
   </details>
   {consent==='declined'&&<p className="warning" role="status">{t('declined')}</p>}
   {consent==='accepted'&&<p role="status">{t('agreed')}</p>}
   {consent==='accepted'&&!sessionId&&<p className="warning" role="status">{t('sessionMissing')}</p>}
   {consentFailure&&<p className="error" role="alert">{failureMessage(consentFailure,t)}</p>}
   <div className="actions">
    <button type="button" className="button secondary" aria-pressed={consent==='accepted'} disabled={consentBusy} onClick={()=>void chooseConsent('accepted')}>{consentBusy?t('consentBusy'):t('agree')}</button>
    <button type="button" className="button secondary" aria-pressed={consent==='declined'} disabled={consentBusy} onClick={()=>void chooseConsent('declined')}>{t('decline')}</button>
    {consent==='accepted'&&sessionId&&<ButtonLink href="/patient/identify">{t('next')}</ButtonLink>}
   </div>
  </div>
 </div>;
}
function Identify(){
 const {t,sessionId,identification,identifying,identificationFailure,identifyFromPhoto,identifyFromNumber,clearIdentification,cancelIdentification}=useApp();
 const [number,setNumber]=useState('');
 const [hospital,setHospital]=useState('');
 const [numberError,setNumberError]=useState(false);
 const [file,setFile]=useState<File|null>(null);
 const [preview,setPreview]=useState('');
 const [fileError,setFileError]=useState<TranslationKey|null>(null);
 const input=useRef<HTMLInputElement>(null);
 const numberField=useRef<HTMLInputElement>(null);
 const busy=identifying;
 useEffect(()=>{if(!file){setPreview('');return}const url=URL.createObjectURL(file);setPreview(url);return()=>URL.revokeObjectURL(url)},[file]);
 function resetFile(){setFile(null);setFileError(null);if(input.current)input.current.value=''}
 function chooseFile(f:File|undefined){if(!f)return;clearIdentification();if(!['image/jpeg','image/png','image/webp'].includes(f.type)||f.size>5*1024*1024){setFile(null);setFileError('invalidFile');if(input.current)input.current.value='';return}setFileError(null);setFile(f)}
 function submitPhoto(){if(!file||busy)return;void identifyFromPhoto(file)}
 function submitNumber(e:FormEvent){e.preventDefault();if(busy)return;const cleaned=number.trim();if(!/^[a-zA-Z0-9][a-zA-Z0-9\-/.]{2,31}$/.test(cleaned)){setNumberError(true);return}setNumberError(false);void identifyFromNumber(cleaned,hospital.trim())}
 function focusNumber(){clearIdentification();setNumberError(false);numberField.current?.focus()}
 return <div className="page">
  <PageHeading title={t('identifyTitle')} intro={t('identifyIntro')} back="/patient"/>
  <Demo short/>
  {!sessionId&&<div className="warning" role="status"><Info size={18} aria-hidden="true"/><span>{t('sessionMissing')} <Link className="inline-link" href="/patient">{t('reviewConsent')}</Link></span></div>}
  <div className="identify-grid">
   <section className="panel">
    <div className="panel-icon"><UploadCloud size={25}/></div>
    <h2>{t('upload')}</h2>
    <p>{t('uploadText')}</p>
    <div className="upload-zone" onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();chooseFile(e.dataTransfer.files[0])}}>
     <UploadCloud size={30} aria-hidden="true"/>
     <p>{t('uploadHint')}</p>
     <p>{t('dropPhoto')}</p>
     <input ref={input} id="bill-photo" type="file" accept="image/jpeg,image/png,image/webp" onChange={e=>chooseFile(e.target.files?.[0])} aria-describedby="photo-hint"/>
     <label className="button secondary" htmlFor="bill-photo">{t(file?'replace':'choose')}</label>
    </div>
    <p className="hint" id="photo-hint">{t('photoNote')}</p>
    {fileError&&<p role="alert" className="error">{t(fileError)}</p>}
    {file&&preview&&<div className="photo-preview">
     <Image unoptimized width={400} height={200} src={preview} alt="" onError={()=>{setFile(null);setFileError('unreadable');if(input.current)input.current.value=''}}/>
     <p>{t('filename')}: {file.name}</p>
     <p>{t('photoReady')}</p>
     <div className="actions">
      <button type="button" className="button primary" onClick={submitPhoto} disabled={busy||!sessionId}>{t('usePhoto')}</button>
      <button type="button" className="button secondary" onClick={()=>{resetFile();clearIdentification()}} disabled={busy}>{t('remove')}</button>
     </div>
    </div>}
   </section>
   <div className="or-divider">{t('or')}</div>
   <section className="panel">
    <div className="panel-icon"><FileText size={25}/></div>
    <h2>{t('numberTitle')}</h2>
    <p>{t('numberIntro')}</p>
    <form onSubmit={submitNumber} noValidate>
     <label htmlFor="bill-number">{t('billNumber')}</label>
     <input ref={numberField} id="bill-number" value={number} onChange={e=>{setNumber(e.target.value);setNumberError(false);clearIdentification()}} placeholder={t('numberPlaceholder')} autoComplete="off" aria-invalid={numberError} aria-describedby={numberError?'number-error':undefined}/>
     {numberError&&<p className="error" id="number-error" role="alert">{t('numberError')}</p>}
     <label htmlFor="hospital-identifier">{t('hospitalLabel')}</label>
     <input id="hospital-identifier" value={hospital} onChange={e=>setHospital(e.target.value)} placeholder={t('hospitalPlaceholder')} autoComplete="off" aria-describedby="hospital-hint"/>
     <p className="hint" id="hospital-hint">{t('hospitalHint')}</p>
     <div className="actions">
      <button type="button" className="button secondary" onClick={()=>{setNumber('');setHospital('');setNumberError(false);clearIdentification()}} disabled={busy}>{t('clear')}</button>
      <button className="button primary" type="submit" disabled={busy||!sessionId}>{t('findBill')} <ArrowRight size={18} aria-hidden="true"/></button>
     </div>
    </form>
   </section>
  </div>
  {identifying&&<div className="status-box" role="status" aria-live="polite"><UploadCloud size={24} aria-hidden="true"/><div><h2>{t('loading')}</h2><p>{t('identifyChecking')}</p><div className="actions"><button type="button" className="button secondary" onClick={cancelIdentification}>{t('cancel')}</button></div></div></div>}
  {!identifying&&identificationFailure&&<FailureNotice title={t('identifyProblem')} failure={identificationFailure}/>}
  {!identifying&&identification&&<div className={`status-box ${identification.status==='access_code_required'?'':'status-warning'}`} role="status" aria-live="polite">
   {identification.status==='access_code_required'?<CheckCircle2 size={26} aria-hidden="true"/>:<AlertCircle size={26} aria-hidden="true"/>}
   <div>
    <h2>{identification.status==='access_code_required'?t('identifiedTitle'):t('identifyProblem')}</h2>
    {identification.hospital_name&&<p>{t('hospitalName')}: <strong>{identification.hospital_name}</strong></p>}
    {identification.bill_number&&<p>{t('billId')}: <strong>{identification.bill_number}</strong></p>}
    <p>{t(IDENTIFICATION_MESSAGES[identification.status])}</p>
    <p className="hint">{t('noAmountsYet')}</p>
    <div className="actions">
     {identification.status==='access_code_required'&&<ButtonLink href="/patient/verify">{t('verifyNext')}</ButtonLink>}
     {MANUAL_RECOVERY.includes(identification.status)&&<button type="button" className="button secondary" onClick={focusNumber}>{t('enterNumber')}</button>}
     {identification.status==='unreadable_image'&&<button type="button" className="button secondary" onClick={()=>{resetFile();clearIdentification()}}>{t('tryPhoto')}</button>}
    </div>
   </div>
  </div>}
  <p className="muted">{t('noRealLookup')} <Link className="inline-link" href="/patient/help">{t('help')}</Link></p>
 </div>;
}
function Verify(){
 const {t,identification,sessionId,verification,verificationFailure,verifying,verifyCode}=useApp();
 const router=useRouter();
 const [code,setCode]=useState('');
 const [error,setError]=useState(false);
 const [show,setShow]=useState(false);
 const busy=useRef(false);
 async function submit(e:FormEvent){
  e.preventDefault();
  if(busy.current||verifying)return;
  busy.current=true;
  if(!/^[a-zA-Z0-9]{4,64}$/.test(code.trim())){setError(true);busy.current=false;return}
  setError(false);
  const ok=await verifyCode(code.trim());
  setCode('');
  busy.current=false;
  if(ok)router.push('/patient/result');
 }
 const incorrect=verificationFailure?.key==='codeIncorrect';
 const failure:ApiFailure=verificationFailure??{code:'verification_unavailable',status:0,key:verification==='locked'?'codeLocked':verification==='expired'?'codeExpired':'identificationMissing',message:''};
 return <div className="page narrow">
  <PageHeading title={t('verifyTitle')} intro={t('verifyIntro')} back="/patient/identify"/>
  <Demo short/>
  <section className="panel">
   <div className="panel-icon"><LockKeyhole size={25}/></div>
   {identification&&<p className="hint">{t('hospitalName')}: <strong>{identification.hospital_name}</strong> · {t('billId')}: <strong>{identification.bill_number}</strong></p>}
   {verification==='pending'?<form onSubmit={submit} noValidate>
    <p>{t('codeIntro')}</p>
    <label htmlFor="code">{t('code')}</label>
    <input id="code" type={show?'text':'password'} value={code} onChange={e=>{setCode(e.target.value);setError(false)}} autoComplete="off" placeholder={t('codePlaceholder')} aria-describedby="code-hint" aria-invalid={error||incorrect}/>
    <p id="code-hint" className="hint">{t('attemptLimit')}</p>
    {error&&<p className="error" role="alert">{t('codeError')}</p>}
    {verificationFailure&&<p className="error" role="alert">{failureMessage(verificationFailure,t)}</p>}
    <div className="actions">
     <button type="button" className="button secondary" onClick={()=>setShow(!show)}>{t(show?'hideCode':'showCode')}</button>
     <button type="button" className="button secondary" onClick={()=>{setCode('');setError(false)}} disabled={verifying}>{t('clear')}</button>
     <button className="button primary" type="submit" disabled={verifying||!sessionId}>{verifying?t('loading'):t('verify')}</button>
    </div>
   </form>
   :verification==='verified'?<div className="status-box" role="status"><CheckCircle2 size={24} aria-hidden="true"/><div><h2>{t('verificationComplete')}</h2><p>{t('verifiedDemo')}</p><div className="actions"><ButtonLink href="/patient/result">{t('verificationResult')}</ButtonLink></div></div></div>
   :<><FailureNotice title={t('verificationFailed')} failure={failure}/><div className="actions"><ButtonLink href="/patient/identify">{t('retry')}</ButtonLink></div></>}
  </section>
  <p className="muted">{t('trouble')} <Link className="inline-link" href="/patient/help">{t('help')}</Link></p>
 </div>;
}
function Result(){
 const {t,verificationDetail,identification,bill}=useApp();
 const comparison=verificationDetail?.comparison??bill?.comparison??null;
 return <div className="page narrow">
  <PageHeading title={t('verificationResult')} intro={t('verifiedDemo')} back="/patient/verify"/>
  <Demo short/>
  <div className="status-box" role="status">
   <CheckCircle2 size={26} aria-hidden="true"/>
   <div>
    <h2>{t('verificationComplete')}</h2>
    <p>{t('verifiedDemo')}</p>
    {identification&&<p className="hint">{t('hospitalName')}: {identification.hospital_name} · {t('billId')}: {identification.bill_number}</p>}
    {verificationDetail&&<p className="hint">{t('verifiedAt')}: {formatTimestamp(verificationDetail.verified_at)}</p>}
    {comparison&&<p className="hint">{t('comparisonLabel')}: {t(comparisonKey(comparison.status))}</p>}
    <div className="actions"><ButtonLink href="/patient/bill">{t('viewBill')}</ButtonLink></div>
   </div>
  </div>
 </div>;
}
function Bill(){
 const {t,bill,billState,loadBill,verification}=useApp();
 useEffect(()=>{if(verification==='verified'&&billState.status==='idle')void loadBill()},[verification,billState.status,loadBill]);
 const total=formatCurrency(bill?.amounts.total_amount?.value);
 const payable=formatCurrency(bill?.amounts.patient_payable?.value);
 return <div className="page">
  <PageHeading title={t('billTitle')} intro={t('billIntro')} back="/patient/verify"/>
  <Demo/>
  {billState.status==='error'&&<FailureNotice title={t('billLoadFailed')} failure={billState.failure} onRetry={()=>void loadBill()}/>}
  {!bill&&billState.status!=='error'&&<section className="panel" role="status"><p>{t('loading')}</p></section>}
  {bill&&<section className="panel bill-panel">
   <div className="bill-header">
    <div>
     <span className="eyebrow">{t('verifiedRecord')}</span>
     <h2>{bill.hospital_name}</h2>
     <p>{t('billId')}: {bill.bill_number} &nbsp; · &nbsp; {t('billDate')}: {formatDate(bill.bill_date)}</p>
     <p className="hint">{t('verifiedAt')}: {formatTimestamp(bill.verified_at)}</p>
    </div>
    <FileHeart size={32} aria-hidden="true"/>
   </div>
   <div className="amount-grid">
    <div className="amount"><span>{t('total')}</span><strong>{total??t('unavailable')}</strong><p>{t('totalDesc')}</p></div>
    <div className="amount highlight"><span>{t('payable')}</span><strong>{payable??t('unavailable')}</strong><p>{t('payableDesc')}</p></div>
   </div>
   <p className="hint">{t('missingAmountsNote')}</p>
   <p className="hint">{t('insuranceMissing')}</p>
   {bill.comparison&&<div className={`status-box ${bill.comparison.status==='amounts_differ'?'status-warning':''}`} role="status"><Info size={20} aria-hidden="true"/><div><h2>{t('comparisonLabel')}</h2><p>{t(comparisonKey(bill.comparison.status))}</p></div></div>}
   {bill.uploaded_amounts&&bill.uploaded_amounts.length>0&&<details><summary>{t('uploadedAmounts')}</summary><ul>{bill.uploaded_amounts.map((amount,i)=><li key={`${amount.label}-${i}`}>{amount.label==='total'?t('total'):t('payable')}: {formatCurrency(amount.value)??amount.value}</li>)}</ul><p className="hint">{t('uploadedNotOfficial')}</p></details>}
   <details><summary>{t('details')}</summary><p>{t('billDate')}: {formatDate(bill.bill_date)}</p><p>{t('billNotice')}</p></details>
   <Glossary/>
   <div className="actions">
    <ButtonLink href="/patient/explanation">{t('explain')}</ButtonLink>
    <ButtonLink href="/patient/questions" secondary>{t('ask')}</ButtonLink>
    <ButtonLink href="/caregiver" secondary>{t('caregiver')}</ButtonLink>
   </div>
  </section>}
  <SupportLink/>
 </div>;
}
function Glossary(){const {t}=useApp();return <details className="glossary"><summary>{t('glossary')}</summary>{([['insurance','answerInsurance'],['payable','answerPay'],['paid','paidDesc']] as const).map(([term,definition])=><details key={term}><summary>{t(term)}</summary><p>{t(definition)}</p></details>)}</details>}
function SupportLink(){const {t}=useApp();return <div className="support-link"><CircleHelp size={21}/><span>{t('helpTitle')}</span><Link href="/patient/help">{t('help')} <ArrowRight size={16}/></Link></div>}
function Explanation(){
 const {t,language,bill,billState,loadBill,verification}=useApp();
 const [simple,setSimple]=useState(false);
 const [speech,setSpeech]=useState<'idle'|'playing'|'paused'>('idle');
 const [available,setAvailable]=useState(false);
 const [voiceMissing,setVoiceMissing]=useState(false);
 useEffect(()=>{if(verification==='verified'&&billState.status==='idle')void loadBill()},[verification,billState.status,loadBill]);
 useEffect(()=>{setAvailable('speechSynthesis' in window && 'SpeechSynthesisUtterance' in window);return()=>{if('speechSynthesis' in window)window.speechSynthesis.cancel()}},[]);
 useEffect(()=>{setSpeech('idle');setVoiceMissing(false)},[language]);
 const values={total:formatCurrency(bill?.amounts.total_amount?.value)??t('unavailable'),payable:formatCurrency(bill?.amounts.patient_payable?.value)??t('unavailable')};
 const sections=([['explanation1Title','explanation1'],['explanation2Title','explanation2'],['explanation3Title','explanation3']] as const);
 const simpleText=fillTemplate(t('simpleText'),values);
 function play(){
  if(!available)return;
  window.speechSynthesis.cancel();
  const utterance=new SpeechSynthesisUtterance(simple?simpleText:sections.map(([,p])=>fillTemplate(t(p),values)).join(' '));
  utterance.lang={en:'en-IN',hi:'hi-IN',kn:'kn-IN'}[language];
  const voice=window.speechSynthesis.getVoices().find(v=>v.lang.toLowerCase().startsWith(language));
  if(voice)utterance.voice=voice;else setVoiceMissing(true);
  utterance.onend=()=>setSpeech('idle');
  utterance.onerror=()=>setSpeech('idle');
  window.speechSynthesis.speak(utterance);
  setSpeech('playing');
 }
 return <div className="page narrow">
  <PageHeading title={t('explainTitle')} intro={t('explainIntro')} back="/patient/bill"/>
  <Demo/>
  {billState.status==='error'&&<FailureNotice title={t('billLoadFailed')} failure={billState.failure} onRetry={()=>void loadBill()}/>}
  {!bill&&billState.status!=='error'&&<section className="panel" role="status"><p>{t('loading')}</p></section>}
  {bill&&<div className="panel explanation">
   <div className="explanation-top"><span className="eyebrow">{t('fixed')}</span><div className="listen-controls"><button className="button secondary" onClick={play} disabled={!available}><Volume2 size={18}/>{t('listen')}</button>{speech!=='idle'&&<><button className="button secondary" onClick={()=>{if(speech==='playing'){window.speechSynthesis.pause();setSpeech('paused')}else{window.speechSynthesis.resume();setSpeech('playing')}}}>{t(speech==='playing'?'pause':'resume')}</button><button className="button secondary" onClick={()=>{window.speechSynthesis.cancel();setSpeech('idle')}}>{t('stop')}</button></>}</div></div>
   {!available&&<p className="hint">{t('speechUnavailable')}</p>}
   {voiceMissing&&<p className="hint">{t('voiceUnavailable')}</p>}
   <p role="status">{t('recordingStatus')}: {t(speech)}</p>
   <p className="hint">{t('advice')}</p>
   {!simple&&<><h2 className="subheading">{t('original')}</h2>{sections.map(([h,p])=><div className="explanation-section" key={h}><h3>{t(h)}</h3><p>{fillTemplate(t(p),values)}</p></div>)}</>}
   <button className="button secondary" aria-pressed={simple} onClick={()=>{if('speechSynthesis' in window)window.speechSynthesis.cancel();setSpeech('idle');setSimple(!simple)}}><Sparkles size={18}/>{t(simple?'showOriginal':'simplify')}</button>
   {simple&&<div className="simple-box"><h3>{t('simpler')}</h3><p>{simpleText}</p></div>}
   <Glossary/>
   <div className="actions"><ButtonLink href="/patient/questions">{t('ask')}</ButtonLink><ButtonLink href="/patient/bill" secondary>{t('backBill')}</ButtonLink></div>
  </div>}
  <SupportLink/>
 </div>;
}
type SpeechRecognitionResultEvent = {results: ArrayLike<ArrayLike<{transcript:string}>>};
type Recognizer = {lang:string;continuous:boolean;interimResults:boolean;onresult:((e:SpeechRecognitionResultEvent)=>void)|null;onerror:(()=>void)|null;onend:(()=>void)|null;start:()=>void;stop:()=>void;abort:()=>void};
type SpeechWindow = Window & {SpeechRecognition?:new()=>Recognizer;webkitSpeechRecognition?:new()=>Recognizer};
function Questions(){const {t,language}=useApp();const [value,setValue]=useState('');const [error,setError]=useState(false);const [messages,setMessages]=useState<{question:string;answer:TranslationKey}[]>([]);const [recording,setRecording]=useState(false);const [voiceError,setVoiceError]=useState<TranslationKey|null>(null);const recognition=useRef<Recognizer|null>(null);useEffect(()=>()=>{recognition.current?.abort();recognition.current=null},[language]);function startVoice(){const w=window as SpeechWindow;const Speech=w.SpeechRecognition||w.webkitSpeechRecognition;if(!Speech){setVoiceError('recognitionUnavailable');return}const r=new Speech();recognition.current=r;r.lang={en:'en-IN',hi:'hi-IN',kn:'kn-IN'}[language];r.continuous=false;r.interimResults=false;r.onresult=e=>{setValue(e.results[0][0].transcript);setVoiceError(null)};r.onerror=()=>{setVoiceError('voiceError');setRecording(false)};r.onend=()=>setRecording(false);try{r.start();setRecording(true);setVoiceError(null)}catch{setVoiceError('voiceError')}}function submit(e:FormEvent){e.preventDefault();if(!value.trim()){setError(true);return}const q=value.trim();let answer:TranslationKey='answerUnavailable';if(q===t('example1'))answer='answerInsurance';if(q===t('example2'))answer='answerPay';setMessages(m=>[...m,{question:q,answer}]);setValue('');setError(false)}return <div className="page narrow"><PageHeading title={t('questionsTitle')} intro={t('questionsIntro')} back="/patient/bill"/><Demo/><div className="panel"><h2>{t('examples')}</h2><div className="examples"><button onClick={()=>setValue(t('example1'))}>{t('example1')}</button><button onClick={()=>setValue(t('example2'))}>{t('example2')}</button></div><form onSubmit={submit} noValidate><label htmlFor="question">{t('questionLabel')}</label><textarea id="question" value={value} onChange={e=>setValue(e.target.value)} placeholder={t('questionPlaceholder')} aria-invalid={error}/>{error&&<p role="alert" className="error">{t('questionError')}</p>}<div className="voice-row"><button type="button" className="button secondary" onClick={()=>recording?recognition.current?.stop():startVoice()}><Mic size={18}/>{t(recording?'stopRecording':'voice')}</button><span>{t(recording?'recording':'voiceReview')} ({language.toUpperCase()})</span></div>{voiceError&&<p className="error" role="alert">{t(voiceError)}</p>}<button className="button primary" type="submit">{t('send')} <ArrowRight size={18}/></button></form></div>{messages.length>0&&<button className="button secondary" onClick={()=>setMessages([])}>{t('clearHistory')}</button>}<div className="conversation" aria-live="polite">{messages.length===0?<p className="empty">{t('noQuestions')}</p>:messages.map((m,i)=><article className="panel" key={i}><span className="eyebrow">{t('question')}</span><h3>{m.question}</h3><div className="response"><strong>{t('response')}</strong><p>{t(m.answer)}</p></div></article>)}</div><SupportLink/></div>}
function Help(){const {t,language}=useApp();const [reason,setReason]=useState('');const [preferred,setPreferred]=useState<Language>(language);const [callback,setCallback]=useState<'now'|'morning'|'afternoon'|'evening'>('now');const [reference,setReference]=useState('');const [permission,setPermission]=useState(false);const [submitted,setSubmitted]=useState(false);const [tried,setTried]=useState(false);function submit(e:FormEvent){e.preventDefault();if(submitted)return;setTried(true);if(!reason.trim()||!permission)return;setReference(`DEMO-${Math.random().toString(36).slice(2,8).toUpperCase()}`);setSubmitted(true)}return <div className="page narrow"><PageHeading title={t('helpPage')} intro={t('helpIntro')}/><div className="warning"><Info size={20}/>{t('helpDemo')}</div>{submitted?<div className="panel success"><CheckCircle2 size={36}/><h2>{t('requestDone')}</h2><p>{t('requestDoneText')}</p><p>{t('requestReference')}: {reference}</p><h3>{t('requestPreferences')}</h3><p>{t('preferredLanguage')}: {{en:'English',hi:'हिन्दी',kn:'ಕನ್ನಡ'}[preferred]} · {t('callback')}: {t(callback)}</p><p>{t('reason')}: {reason}</p><div className="actions"><button className="button secondary" onClick={()=>setSubmitted(false)}>{t('back')}</button><button className="button secondary" onClick={()=>{setSubmitted(false);setPermission(false);setReason('');setTried(false)}}>{t('another')}</button><ButtonLink href="/" secondary>{t('home')}</ButtonLink></div></div>:<form className="panel" onSubmit={submit} noValidate><label htmlFor="preferred-language">{t('preferredLanguage')}</label><select id="preferred-language" value={preferred} onChange={e=>setPreferred(e.target.value as Language)}><option value="en">English</option><option value="hi">हिन्दी</option><option value="kn">ಕನ್ನಡ</option></select><label htmlFor="callback">{t('callback')}</label><select id="callback" value={callback} onChange={e=>setCallback(e.target.value as typeof callback)}><option value="now">{t('now')}</option><option value="morning">{t('morning')}</option><option value="afternoon">{t('afternoon')}</option><option value="evening">{t('evening')}</option></select><label htmlFor="reason">{t('reason')} <span className="muted">({t('required')})</span></label><textarea id="reason" value={reason} onChange={e=>setReason(e.target.value)} placeholder={t('reasonPlaceholder')} aria-invalid={tried&&!reason.trim()}/>{tried&&!reason.trim()&&<p className="error" role="alert">{t('reasonError')}</p>}<label className="checkbox"><input type="checkbox" checked={permission} onChange={e=>setPermission(e.target.checked)}/><span>{t('permission')}</span></label>{tried&&!permission&&<p className="error" role="alert">{t('permissionError')}</p>}<button className="button primary" type="submit">{t('sendRequest')} <ArrowRight size={18}/></button></form>}</div>}
function Caregiver(){
 const {t,bill,billState,loadBill,verification}=useApp();
 useEffect(()=>{if(verification==='verified'&&billState.status==='idle')void loadBill()},[verification,billState.status,loadBill]);
 const payable=formatCurrency(bill?.amounts.patient_payable?.value);
 return <div className="page narrow">
  <PageHeading title={t('caregiverTitle')} intro={t('caregiverIntro')} back="/patient/bill"/>
  <Demo/>
  <div className="warning"><Info size={20} aria-hidden="true"/>{t('caregiverNotice')}</div>
  {billState.status==='error'&&<FailureNotice title={t('billLoadFailed')} failure={billState.failure} onRetry={()=>void loadBill()}/>}
  {!bill&&billState.status!=='error'&&<section className="panel" role="status"><p>{t('loading')}</p></section>}
  {bill&&<div className="panel caregiver">
   {([['mainDetails',null],['terms','termsText'],['dates',null],['clarify','clarifyText'],['nextSteps','nextStepsText']] as const).map(([h,p])=><details key={h} open={h!=='mainDetails'}><summary>{t(h)}</summary><p>{p?t(p):h==='mainDetails'?`${bill.hospital_name} · ${t('payable')}: ${payable??t('unavailable')}`:`${t('billDate')}: ${formatDate(bill.bill_date)}`}</p></details>)}
   <div className="actions"><ButtonLink href="/patient/bill" secondary>{t('returnPatient')}</ButtonLink><ButtonLink href="/patient/help">{t('help')}</ButtonLink></div>
  </div>}
 </div>;
}
type TicketStatus='new'|'scheduled'|'contacted'|'resolved';
function Dashboard(){const {t}=useApp();const [search,setSearch]=useState('');const [filter,setFilter]=useState<TicketStatus|'all'>('all');const [feedback,setFeedback]=useState<TranslationKey|null>(null);const [selected,setSelected]=useState(0);const [statuses,setStatuses]=useState<TicketStatus[]>(['new','scheduled','contacted','resolved']);const tickets=[{id:'DEMO-001',reason:'Insurance coverage',language:'English',callback:'Morning'},{id:'DEMO-002',reason:'Understanding a charge',language:'हिन्दी',callback:'Afternoon'},{id:'DEMO-003',reason:'Payment question',language:'ಕನ್ನಡ',callback:'Evening'},{id:'DEMO-004',reason:'Bill explanation',language:'English',callback:'Now'}];return <div className="page"><PageHeading title={t('dashboard')} intro={t('dashboardIntro')}/><Demo short/><div className="dashboard-grid"><section className="panel"><div className="dashboard-title"><h2>{t('requests')}</h2><span className="tag">{t('demoData')}</span></div><label htmlFor="search">{t('search')}</label><input id="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder={t('searchPlaceholder')}/><label htmlFor="status-filter">{t('statusFilter')}</label><select id="status-filter" value={filter} onChange={e=>setFilter(e.target.value as TicketStatus|'all')}><option value="all">{t('allStatuses')}</option>{(['new','scheduled','contacted','resolved'] as const).map(status=><option key={status} value={status}>{t(status)}</option>)}</select><button className="button secondary" onClick={()=>{setSearch('');setFilter('all');setSelected(0);setStatuses(['new','scheduled','contacted','resolved']);setFeedback('resetDone')}}>{t('resetDemo')}</button>{feedback&&<p role="status">{t(feedback)}</p>}<div className="ticket-list">{tickets.map((ticket,i)=>(filter==='all'||statuses[i]===filter)&&`${ticket.id} ${ticket.reason}`.toLowerCase().includes(search.toLowerCase())&&<button key={ticket.id} className={`ticket ${selected===i?'selected':''}`} onClick={()=>setSelected(i)}><span><strong>{ticket.id}</strong><small>{t('fictional')}</small></span><span className={`status ${statuses[i]}`}>{t(statuses[i])}</span></button>)}{!tickets.some((ticket,i)=>(filter==='all'||statuses[i]===filter)&&`${ticket.id} ${ticket.reason}`.toLowerCase().includes(search.toLowerCase()))&&<p>{t('noResults')}</p>}</div></section>{(filter==='all'||statuses[selected]===filter)&&`${tickets[selected].id} ${tickets[selected].reason}`.toLowerCase().includes(search.toLowerCase())?<section className="panel"><h2>{t('requestDetails')}</h2><span className="tag">{t('demoData')}</span><h3>{tickets[selected].id}</h3><dl className="details"><div><dt>{t('caseSummary')}</dt><dd>{t('fictional')}</dd></div><div><dt>{t('reason')}</dt><dd><span lang="en">{tickets[selected].reason}</span>{languageLimitation(t)}</dd></div><div><dt>{t('preferredLanguage')}</dt><dd>{tickets[selected].language}</dd></div><div><dt>{t('callbackPreference')}</dt><dd><span lang="en">{tickets[selected].callback}</span>{languageLimitation(t)}</dd></div></dl><label htmlFor="status">{t('changeStatus')}</label><select id="status" value={statuses[selected]} onChange={e=>{setStatuses(statuses.map((s,i)=>i===selected?e.target.value as TicketStatus:s));setFeedback('statusChanged')}}><option value="new">{t('new')}</option><option value="scheduled">{t('scheduled')}</option><option value="contacted">{t('contacted')}</option><option value="resolved">{t('resolved')}</option></select><p className="hint">{t('notSaved')}</p></section>:<section className="panel"><p>{t('selectRequest')}</p></section>}</div></div>}
function languageLimitation(t:(key:TranslationKey)=>string){return t('home')==='Home'?null:<small> [English demo data]</small>}
const steps = [ ['/patient','progressConsent'], ['/patient/identify','progressIdentify'], ['/patient/verify','progressVerify'], ['/patient/result','progressResult'], ['/patient/bill','progressBill'], ['/patient/explanation','progressExplain'] ] as const;
function Progress({path}:{path:string}){
 const {t,consent,identification,verification,restart}=useApp();
 const current=steps.findIndex(([href])=>href===path);
 if(current<0)return null;
 const identified=identification?.status==='access_code_required';
 return <nav className="progress container" aria-label={t('progress')}>
  <ol>{steps.map(([href,label],i)=>{
   const complete=i===0?consent==='accepted':i===1?identified:i===2?verification==='verified':false;
   const reachable=i===0||(i===1&&consent==='accepted')||(i===2&&identified)||(i>=3&&identified&&verification==='verified');
   return <li key={href} aria-current={i===current?'step':undefined}>{reachable?<Link href={href}>{i+1}. {t(label)}{complete?' ✓':''}</Link>:<span>{i+1}. {t(label)}</span>}</li>
  })}</ol>
  <Link href="/" onClick={restart}>{t('restart')}</Link>
 </nav>;
}
export function Navigator(){
 const path=usePathname();
 const {t,consent,identification,verification}=useApp();
 let page:React.ReactNode;
 const needsConsent=['/patient/identify','/patient/verify','/patient/result','/patient/bill','/patient/explanation','/patient/questions','/caregiver'].includes(path);
 const needsIdentification=['/patient/verify','/patient/result','/patient/bill','/patient/explanation','/patient/questions','/caregiver'].includes(path);
 const needsVerified=['/patient/result','/patient/bill','/patient/explanation','/patient/questions','/caregiver'].includes(path);
 const identified=identification?.status==='access_code_required';
 let recover:string|null=null;
 if(needsConsent&&consent!=='accepted')recover='/patient';
 else if(needsIdentification&&!identified)recover='/patient/identify';
 else if(needsVerified&&verification!=='verified')recover='/patient/verify';
 if(recover){page=<div className="page narrow"><PageHeading title={t('unavailable')} intro={t('missingState')}/><Demo short/><ButtonLink href={recover}>{t('next')}</ButtonLink></div>}
 else switch(path){case '/':page=<Home/>;break;case '/patient':page=<Consent/>;break;case '/patient/identify':page=<Identify/>;break;case '/patient/verify':page=<Verify/>;break;case '/patient/result':page=<Result/>;break;case '/patient/bill':page=<Bill/>;break;case '/patient/explanation':page=<Explanation/>;break;case '/patient/questions':page=<Questions/>;break;case '/patient/help':page=<Help/>;break;case '/caregiver':page=<Caregiver/>;break;case '/support':page=<Dashboard/>;break;default:page=<div className="page"><h1>Page not found</h1><Link href="/">{t('home')}</Link></div>}
 return <><Header/><main id="main"><Progress path={path}/>{page}</main><Footer/></>;
}
