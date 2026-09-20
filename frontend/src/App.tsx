import { NavLink, Route, Routes } from "react-router-dom";
import "./styles.css";

const cards = [
  ["Active Sessions","0","Live and upcoming experiences"],
  ["Participants","0","People currently assigned"],
  ["Evaluations","0","Awaiting review or release"],
  ["Organizations","1","Licensed organizations"],
];

function Placeholder({title, text}:{title:string;text:string}) {
  return <Page title={title}><section className="panel"><h2>{title}</h2><p>{text}</p>
    <div className="empty"><strong>Ready for data</strong><span>This interface is wired into the application shell and ready for the next API build.</span></div>
  </section></Page>;
}
function Page({title,children}:{title:string;children:React.ReactNode}) {
 return <main><header className="topbar"><div><span className="eyebrow">ALI SIMULATIONS</span><h1>{title}</h1></div><div className="avatar">PA</div></header>{children}</main>;
}
function Dashboard(){
 return <Page title="Platform Overview"><section className="hero"><div><span className="eyebrow">LEADERSHIP, EXPERIENCED.</span><h2>Build experiences that reveal how people lead.</h2><p>Manage organizations, launch simulations, observe leadership behavior, and turn experience into meaningful feedback.</p></div><button>+ New Session</button></section>
 <section className="metrics">{cards.map(([a,b,c])=><article className="metric" key={a}><span>{a}</span><strong>{b}</strong><small>{c}</small></article>)}</section>
 <section className="grid"><article className="panel"><div className="panelhead"><h2>Upcoming & Active Sessions</h2><button className="quiet">View all</button></div><div className="empty"><strong>No active sessions yet</strong><span>Create a session when you're ready to begin testing an experience.</span></div></article>
 <article className="panel"><h2>Platform Readiness</h2><div className="check">✓ Authentication foundation</div><div className="check">✓ Organization & licensing model</div><div className="check">✓ Scenario/version foundation</div><div className="check">✓ Audit architecture</div><div className="next">NEXT · People, sessions & evaluations</div></article></section></Page>
}
const nav=[["/","Home"],["/organizations","Organizations"],["/people","People"],["/simulations","Programs & Simulations"],["/sessions","Sessions"],["/leadership","Leadership Development"],["/communications","Communications"],["/reports","Reports"],["/admin","Administration"]];
export default function App(){
 return <div className="app"><aside><div className="brand"><div className="mark">▲</div><div><b>ALI</b><span>SIMULATIONS</span><small>Leadership, Experienced.</small></div></div><nav>{nav.map(([u,n])=><NavLink key={u} to={u} end={u==="/"}>{n}</NavLink>)}</nav><div className="user"><b>Platform Administrator</b><span>Development environment</span></div></aside>
 <Routes><Route path="/" element={<Dashboard/>}/><Route path="/organizations" element={<Placeholder title="Organizations" text="Manage licensed organizations, administrators, branding, simulation entitlements, and access."/>}/><Route path="/people" element={<Placeholder title="People" text="One canonical directory for participants, evaluators, staff, volunteers, and external contacts."/>}/><Route path="/simulations" element={<Placeholder title="Programs & Simulations" text="Manage Belonging, CityLab, and future ALI simulation experiences."/>}/><Route path="/sessions" element={<Placeholder title="Sessions" text="Create, operate, and review upcoming, active, and completed simulation sessions."/>}/><Route path="/leadership" element={<Placeholder title="Leadership Development" text="Review observations, evaluations, approvals, participant releases, rubrics, and leadership journeys."/>}/><Route path="/communications" element={<Placeholder title="Communications" text="Compose participant and evaluator communications using relationship-based audiences and templates."/>}/><Route path="/reports" element={<Placeholder title="Reports" text="Participant, session, program, organization, and simulation outcome reporting."/>}/><Route path="/admin" element={<Placeholder title="Administration" text="Branding, access, consent templates, licensing, platform settings, and audit history."/>}/></Routes></div>
}