import { useState } from "react";

function AlignmentMark({ size = 80, color = "#2D8C78" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none">
      <ellipse cx="50" cy="18" rx="8" ry="5.5" fill={color} opacity="0.55" />
      <ellipse cx="49" cy="30" rx="10.5" ry="6" fill={color} opacity="0.65" />
      <ellipse cx="48" cy="43" rx="13" ry="6.5" fill={color} opacity="0.75" />
      <ellipse cx="49" cy="56.5" rx="14" ry="6.5" fill={color} opacity="0.85" />
      <ellipse cx="50" cy="70" rx="13" ry="6.5" fill={color} opacity="0.92" />
      <ellipse cx="51" cy="83" rx="10.5" ry="5.5" fill={color} />
      <line x1="50" y1="10" x2="50" y2="91" stroke={color} strokeWidth="1.5" strokeDasharray="2 3" opacity="0.3" />
      <path d="M50 11 C50 5 56 2 60 5 C58 8 54 10 50 11Z" fill={color} opacity="0.7" />
      <path d="M50 11 C50 5 44 2 40 5 C42 8 46 10 50 11Z" fill={color} opacity="0.5" />
    </svg>
  );
}

function PathwayMark({ size = 80, color = "#2D8C78" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none">
      <path d="M38 88 C36 72 34 58 36 48 C38 36 42 26 50 16" stroke={color} strokeWidth="5" strokeLinecap="round" fill="none" />
      <path d="M62 88 C64 72 66 58 64 48 C62 36 58 26 50 16" stroke={color} strokeWidth="5" strokeLinecap="round" fill="none" />
      <line x1="42" y1="76" x2="58" y2="76" stroke={color} strokeWidth="2" strokeLinecap="round" opacity="0.3" />
      <line x1="41" y1="64" x2="59" y2="64" stroke={color} strokeWidth="2" strokeLinecap="round" opacity="0.3" />
      <line x1="40" y1="52" x2="60" y2="52" stroke={color} strokeWidth="2" strokeLinecap="round" opacity="0.3" />
      <line x1="42" y1="40" x2="58" y2="40" stroke={color} strokeWidth="2" strokeLinecap="round" opacity="0.3" />
      <line x1="45" y1="29" x2="55" y2="29" stroke={color} strokeWidth="2" strokeLinecap="round" opacity="0.3" />
      <circle cx="50" cy="10" r="4.5" fill={color} />
    </svg>
  );
}

function HelixMark({ size = 80, color = "#2D8C78" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none">
      <path d="M36 14 C54 22 54 32 36 40 C18 48 18 58 36 66 C54 74 54 84 36 90" stroke={color} strokeWidth="3.5" strokeLinecap="round" fill="none" />
      <path d="M64 14 C46 22 46 32 64 40 C82 48 82 58 64 66 C46 74 46 84 64 90" stroke={color} strokeWidth="3.5" strokeLinecap="round" fill="none" />
      <line x1="40" y1="27" x2="60" y2="27" stroke={color} strokeWidth="2.5" strokeLinecap="round" opacity="0.35" />
      <line x1="36" y1="40" x2="64" y2="40" stroke={color} strokeWidth="2.5" strokeLinecap="round" opacity="0.35" />
      <line x1="40" y1="53" x2="60" y2="53" stroke={color} strokeWidth="2.5" strokeLinecap="round" opacity="0.35" />
      <line x1="36" y1="66" x2="64" y2="66" stroke={color} strokeWidth="2.5" strokeLinecap="round" opacity="0.35" />
      <line x1="40" y1="79" x2="60" y2="79" stroke={color} strokeWidth="2.5" strokeLinecap="round" opacity="0.35" />
    </svg>
  );
}

function ShieldMark({ size = 80, color = "#2D8C78" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none">
      <path d="M50 8 L82 22 L82 50 C82 72 66 88 50 94 C34 88 18 72 18 50 L18 22 Z" stroke={color} strokeWidth="3.5" fill={color} fillOpacity="0.06" strokeLinejoin="round" />
      <path d="M50 26 L50 76" stroke={color} strokeWidth="3" strokeLinecap="round" />
      <circle cx="50" cy="30" r="3" fill={color} />
      <circle cx="50" cy="40" r="3.5" fill={color} />
      <circle cx="50" cy="50" r="4" fill={color} />
      <circle cx="50" cy="60" r="3.5" fill={color} />
      <circle cx="50" cy="70" r="3" fill={color} />
      <path d="M50 42 C44 38 34 36 28 40" stroke={color} strokeWidth="2" strokeLinecap="round" fill="none" opacity="0.35" />
      <path d="M50 42 C56 38 66 36 72 40" stroke={color} strokeWidth="2" strokeLinecap="round" fill="none" opacity="0.35" />
      <path d="M50 58 C44 62 34 64 28 60" stroke={color} strokeWidth="2" strokeLinecap="round" fill="none" opacity="0.35" />
      <path d="M50 58 C56 62 66 64 72 60" stroke={color} strokeWidth="2" strokeLinecap="round" fill="none" opacity="0.35" />
    </svg>
  );
}

function HandsMark({ size = 80, color = "#2D8C78" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none">
      <path d="M14 54 C14 40 22 28 34 22 C40 19 44 20 46 24" stroke={color} strokeWidth="3.5" strokeLinecap="round" fill="none" />
      <path d="M14 54 C16 66 24 76 36 82" stroke={color} strokeWidth="3.5" strokeLinecap="round" fill="none" />
      <path d="M86 54 C86 40 78 28 66 22 C60 19 56 20 54 24" stroke={color} strokeWidth="3.5" strokeLinecap="round" fill="none" />
      <path d="M86 54 C84 66 76 76 64 82" stroke={color} strokeWidth="3.5" strokeLinecap="round" fill="none" />
      <line x1="50" y1="22" x2="50" y2="82" stroke={color} strokeWidth="2.5" strokeLinecap="round" opacity="0.5" />
      <circle cx="50" cy="28" r="3" fill={color} />
      <circle cx="50" cy="38" r="3.5" fill={color} />
      <circle cx="50" cy="49" r="4" fill={color} />
      <circle cx="50" cy="60" r="3.5" fill={color} />
      <circle cx="50" cy="70" r="3" fill={color} />
      <circle cx="50" cy="79" r="2.5" fill={color} opacity="0.7" />
      <path d="M36 82 C42 86 50 88 50 88 C50 88 58 86 64 82" stroke={color} strokeWidth="2.5" strokeLinecap="round" fill="none" opacity="0.5" />
    </svg>
  );
}

const CONCEPTS = [
  { id: "alignment", name: "The Alignment", tagline: "Stacked balance", description: "Vertebrae as graduated, balanced stones — precision of spinal alignment meets the zen of restored balance. The leaf at the crown connects spine to 'Life'.", Mark: AlignmentMark, bestFor: "Clinic signage, letterheads, professional documents" },
  { id: "pathway", name: "The Pathway", tagline: "Open & upward", description: "Two lines trace the spinal column and open upward like a person stretching — freedom from pain. The head dot crowns the human form. Subtle vertebrae cross-bars in the negative space.", Mark: PathwayMark, bestFor: "Website hero, patient portal, app splash screen" },
  { id: "helix", name: "The Helix", tagline: "Science meets life", description: "A double helix that reads as both DNA and a spinal column — life science meets chiropractic. Modern, distinctive, and reflects your evidence-based approach.", Mark: HelixMark, bestFor: "App icon, social media, merchandise" },
  { id: "shield", name: "The Shield", tagline: "Trust & protection", description: "A protective shield containing a vertebral column with subtle hand forms — care, trust, and clinical authority. Exceptional as an app icon and trust badge.", Mark: ShieldMark, bestFor: "App icon, badges, trust indicators, invoices" },
  { id: "hands", name: "The Hands", tagline: "Care in action", description: "Two cupped hands cradling a spine — the most direct expression of chiropractic care. Warm, human, immediately communicates what you do.", Mark: HandsMark, bestFor: "Patient-facing materials, welcome screens, business cards" },
];

const SLOGANS = [
  { text: "Move freely. Live fully.", category: "Patient-centred", why: "Speaks to the outcome patients want" },
  { text: "Aligned to life.", category: "Brand", why: "Short, ties alignment to your name" },
  { text: "Evidence-based. Life-focused.", category: "Clinical", why: "Differentiates from wellness-woo" },
  { text: "Your spine. Your potential.", category: "Aspirational", why: "Empowering, forward-looking" },
  { text: "Better movement starts here.", category: "Action", why: "Clear, inviting, low-barrier" },
  { text: "Care that moves with you.", category: "Relational", why: "Ongoing partnership feel" },
];

const PALETTE = [
  { color: "#2D8C78", name: "Eucalyptus", role: "Primary" },
  { color: "#1E5F51", name: "Deep Forest", role: "Dark" },
  { color: "#4CC9AD", name: "Mint", role: "Light accent" },
  { color: "#A8E6CF", name: "Seafoam", role: "Soft bg" },
  { color: "#191816", name: "Ink", role: "Text" },
  { color: "#F7F6F3", name: "Warm White", role: "Background" },
];

export default function LogoShowcase() {
  const [active, setActive] = useState(0);
  const [sloganIdx, setSloganIdx] = useState(0);
  const [hover, setHover] = useState(null);
  const concept = CONCEPTS[active];
  const Mark = concept.Mark;
  const slogan = SLOGANS[sloganIdx];

  return (
    <>
      <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Satoshi:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
      <style>{`
        *{box-sizing:border-box;margin:0}
        :root{--bg:#F7F6F3;--surface:#FFF;--surface-alt:#F0EFEC;--border:#E4E2DD;--text:#191816;--text-mid:#555249;--text-muted:#8A867D;--accent:#2D8C78;--accent-light:#4CC9AD;--h:'Instrument Serif',serif;--b:'Satoshi',sans-serif}
        @keyframes fu{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
        @keyframes sr{from{opacity:0;transform:scale(.88)}to{opacity:1;transform:scale(1)}}
      `}</style>
      <div style={{minHeight:"100vh",background:"var(--bg)",fontFamily:"var(--b)",color:"var(--text)"}}>
        <header style={{padding:"48px 40px 0",maxWidth:960,margin:"0 auto"}}>
          <div style={{display:"inline-block",fontSize:10,fontWeight:700,letterSpacing:"0.18em",textTransform:"uppercase",color:"var(--accent)",background:"rgba(45,140,120,0.08)",padding:"5px 12px",borderRadius:6,marginBottom:16}}>Brand Identity</div>
          <h1 style={{fontFamily:"var(--h)",fontSize:44,fontWeight:400,lineHeight:1.1,letterSpacing:"-0.02em",marginBottom:10}}>Life Chiropractic</h1>
          <p style={{fontSize:16,color:"var(--text-mid)",lineHeight:1.6,maxWidth:480}}>Five logo concepts and six slogan options. Select a concept, pair it with a slogan, and preview across contexts.</p>
        </header>
        <div style={{maxWidth:960,margin:"0 auto",padding:"32px 40px 80px"}}>
          {/* Concept selector */}
          <div style={{display:"flex",gap:10,marginBottom:32}}>
            {CONCEPTS.map((c,i)=>{const M=c.Mark;const a=i===active;return(
              <button key={c.id} onClick={()=>setActive(i)} onMouseEnter={()=>setHover(i)} onMouseLeave={()=>setHover(null)}
                style={{flex:"1 0 0",minWidth:110,padding:"20px 14px 16px",borderRadius:16,border:a?"2px solid var(--accent)":"1.5px solid var(--border)",background:a?"rgba(45,140,120,0.04)":"var(--surface)",cursor:"pointer",textAlign:"center",transition:"all 0.25s cubic-bezier(.4,0,.2,1)",transform:(a||hover===i)?"translateY(-2px)":"translateY(0)",boxShadow:a?"0 8px 24px rgba(45,140,120,0.1)":hover===i?"0 4px 12px rgba(0,0,0,0.04)":"none"}}>
                <div style={{display:"flex",justifyContent:"center",marginBottom:10}}><M size={48} color={a?"#2D8C78":"#AAA69E"}/></div>
                <div style={{fontSize:12,fontWeight:600,color:a?"var(--text)":"var(--text-muted)",marginBottom:2}}>{c.name}</div>
                <div style={{fontSize:10,color:"var(--text-muted)"}}>{c.tagline}</div>
              </button>
            )})}
          </div>

          <div key={concept.id} style={{animation:"sr 0.4s cubic-bezier(.16,1,.3,1)"}}>
            {/* Hero preview */}
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14,marginBottom:14}}>
              <div style={{background:"#FFF",borderRadius:22,border:"1px solid var(--border)",padding:"52px 32px 44px",textAlign:"center",position:"relative"}}>
                <div style={{position:"absolute",top:16,left:20,fontSize:9,fontWeight:700,letterSpacing:"0.14em",textTransform:"uppercase",color:"var(--text-muted)"}}>Light</div>
                <Mark size={110} color="#2D8C78"/>
                <div style={{marginTop:22,fontFamily:"var(--h)",fontSize:28,color:"#191816"}}>Life Chiropractic</div>
                <div style={{marginTop:6,fontFamily:"var(--h)",fontSize:15,fontStyle:"italic",color:"var(--accent)"}}>{slogan.text}</div>
              </div>
              <div style={{background:"#151917",borderRadius:22,padding:"52px 32px 44px",textAlign:"center",position:"relative"}}>
                <div style={{position:"absolute",top:16,left:20,fontSize:9,fontWeight:700,letterSpacing:"0.14em",textTransform:"uppercase",color:"rgba(255,255,255,0.3)"}}>Dark</div>
                <Mark size={110} color="#4CC9AD"/>
                <div style={{marginTop:22,fontFamily:"var(--h)",fontSize:28,color:"#EDECE9"}}>Life Chiropractic</div>
                <div style={{marginTop:6,fontFamily:"var(--h)",fontSize:15,fontStyle:"italic",color:"#4CC9AD"}}>{slogan.text}</div>
              </div>
            </div>

            {/* Info */}
            <div style={{background:"var(--surface)",borderRadius:18,border:"1px solid var(--border)",padding:"22px 26px",marginBottom:14}}>
              <h3 style={{fontFamily:"var(--h)",fontSize:22,fontWeight:400,marginBottom:6}}>{concept.name}</h3>
              <p style={{fontSize:14,color:"var(--text-mid)",lineHeight:1.65,marginBottom:10}}>{concept.description}</p>
              <div style={{fontSize:12,color:"var(--text-muted)"}}><span style={{fontWeight:600,color:"var(--text-mid)"}}>Best for: </span>{concept.bestFor}</div>
            </div>

            {/* Slogans */}
            <div style={{background:"var(--surface)",borderRadius:18,border:"1px solid var(--border)",padding:"22px 26px",marginBottom:14}}>
              <div style={{fontSize:10,fontWeight:700,letterSpacing:"0.14em",textTransform:"uppercase",color:"var(--text-muted)",marginBottom:14}}>Slogan</div>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8}}>
                {SLOGANS.map((s,i)=>{const a=i===sloganIdx;return(
                  <button key={i} onClick={()=>setSloganIdx(i)} style={{padding:"14px 16px",borderRadius:12,textAlign:"left",cursor:"pointer",border:a?"1.5px solid var(--accent)":"1px solid var(--border)",background:a?"rgba(45,140,120,0.04)":"transparent",transition:"all 0.15s"}}>
                    <div style={{fontFamily:"var(--h)",fontSize:16,fontStyle:"italic",color:a?"var(--text)":"var(--text-mid)",marginBottom:4}}>{s.text}</div>
                    <div style={{display:"flex",gap:8,alignItems:"center"}}>
                      <span style={{fontSize:9,fontWeight:700,letterSpacing:"0.08em",textTransform:"uppercase",padding:"2px 7px",borderRadius:4,background:a?"rgba(45,140,120,0.1)":"var(--surface-alt)",color:a?"var(--accent)":"var(--text-muted)"}}>{s.category}</span>
                      <span style={{fontSize:11,color:"var(--text-muted)"}}>{s.why}</span>
                    </div>
                  </button>
                )})}
              </div>
            </div>

            {/* Usage contexts */}
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:14,marginBottom:14}}>
              {/* App Icons */}
              <div style={{background:"var(--surface)",borderRadius:18,border:"1px solid var(--border)",padding:"22px 20px",textAlign:"center"}}>
                <div style={{fontSize:10,fontWeight:700,letterSpacing:"0.14em",textTransform:"uppercase",color:"var(--text-muted)",marginBottom:16}}>App Icon</div>
                <div style={{display:"flex",justifyContent:"center",gap:14,alignItems:"flex-end"}}>
                  {[{s:56,r:14},{s:40,r:10},{s:28,r:7}].map(({s,r},i)=>(
                    <div key={i} style={{display:"flex",flexDirection:"column",alignItems:"center",gap:6}}>
                      <div style={{width:s,height:s,borderRadius:r,background:"#2D8C78",display:"flex",alignItems:"center",justifyContent:"center",boxShadow:"0 4px 14px rgba(45,140,120,0.25)"}}>
                        <Mark size={s*0.7} color="#FFF"/>
                      </div>
                      <span style={{fontSize:9,color:"var(--text-muted)"}}>{s}px</span>
                    </div>
                  ))}
                </div>
              </div>
              {/* Business Card */}
              <div style={{background:"var(--surface)",borderRadius:18,border:"1px solid var(--border)",padding:"22px 20px",textAlign:"center"}}>
                <div style={{fontSize:10,fontWeight:700,letterSpacing:"0.14em",textTransform:"uppercase",color:"var(--text-muted)",marginBottom:16}}>Business Card</div>
                <div style={{width:"100%",aspectRatio:"1.7/1",background:"#FFF",borderRadius:8,border:"1px solid var(--border)",display:"flex",flexDirection:"column",alignItems:"flex-start",justifyContent:"space-between",padding:"14px 16px",boxShadow:"0 2px 12px rgba(0,0,0,0.05)"}}>
                  <div style={{display:"flex",alignItems:"center",gap:8}}>
                    <Mark size={22} color="#2D8C78"/>
                    <div>
                      <div style={{fontFamily:"var(--h)",fontSize:10,color:"#191816"}}>Life Chiropractic</div>
                      <div style={{fontSize:6,color:"var(--accent)",fontFamily:"var(--h)",fontStyle:"italic"}}>{slogan.text}</div>
                    </div>
                  </div>
                  <div>
                    <div style={{fontSize:8,fontWeight:600,color:"#191816"}}>Dr. Hussein</div>
                    <div style={{fontSize:6,color:"var(--text-muted)"}}>Doctor of Chiropractic</div>
                    <div style={{fontSize:6,color:"var(--text-muted)",marginTop:1}}>hello@lifechiropractic.co.uk</div>
                  </div>
                </div>
              </div>
              {/* Website Nav */}
              <div style={{background:"var(--surface)",borderRadius:18,border:"1px solid var(--border)",padding:"22px 20px",textAlign:"center"}}>
                <div style={{fontSize:10,fontWeight:700,letterSpacing:"0.14em",textTransform:"uppercase",color:"var(--text-muted)",marginBottom:16}}>Website Nav</div>
                <div style={{background:"#FFF",borderRadius:8,border:"1px solid var(--border)",padding:"10px 14px",display:"flex",alignItems:"center",justifyContent:"space-between",boxShadow:"0 2px 12px rgba(0,0,0,0.05)"}}>
                  <div style={{display:"flex",alignItems:"center",gap:6}}>
                    <Mark size={20} color="#2D8C78"/>
                    <span style={{fontFamily:"var(--h)",fontSize:11,color:"#191816"}}>Life Chiropractic</span>
                  </div>
                  <div style={{display:"flex",gap:10,alignItems:"center"}}>
                    {["About","Services","Book"].map((t,i)=>(
                      <span key={t} style={{fontSize:8,color:i===2?"#fff":"var(--text-muted)",fontWeight:500,...(i===2?{background:"var(--accent)",padding:"3px 8px",borderRadius:4}:{})}}>{t}</span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Palette */}
            <div style={{background:"var(--surface)",borderRadius:18,border:"1px solid var(--border)",padding:"22px 26px"}}>
              <div style={{fontSize:10,fontWeight:700,letterSpacing:"0.14em",textTransform:"uppercase",color:"var(--text-muted)",marginBottom:16}}>Brand Palette</div>
              <div style={{display:"flex",gap:10}}>
                {PALETTE.map(p=>(
                  <div key={p.color} style={{flex:1,textAlign:"center"}}>
                    <div style={{height:48,borderRadius:10,background:p.color,border:p.color==="#F7F6F3"?"1px solid var(--border)":"none",marginBottom:8}}/>
                    <div style={{fontSize:11,fontWeight:600,color:"var(--text)"}}>{p.name}</div>
                    <div style={{fontSize:9,color:"var(--text-muted)"}}>{p.role}</div>
                    <div style={{fontSize:9,color:"var(--text-muted)",fontFamily:"monospace",marginTop:2}}>{p.color}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
