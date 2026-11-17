import {
    ArrowRight,
    ArrowUpRight,
    BookOpen,
    Building2,
    CalendarDays,
    CheckCircle2,
    Clock3,
    FileBarChart,
    Fingerprint,
    GraduationCap,
    Layers3,
    QrCode,
    ScanFace,
    ShieldCheck,
    Users,
} from "lucide-react";
import { Link } from "react-router-dom";

function PageIntro({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
    return (
        <section className="page-intro">
            <div className="container page-intro-inner">
                <span className="eyebrow">{eyebrow}</span>
                <h1>{title}</h1>
                <p>{description}</p>
            </div>
        </section>
    );
}

export function HomePage() {
    return (
        <>
            <section className="hero-section">
                <div className="container hero-grid">
                    <div className="hero-copy">
                        <div className="eyebrow"><span className="eyebrow-dot" /> ACADEMIC MANAGEMENT · SMART ATTENDANCE</div>
                        <h1>Attendance, <span>connected.</span></h1>
                        <p className="hero-lead">
                            Bring academic administration, course coordination and a verification-first attendance model into one clear institutional workflow.
                        </p>
                        <div className="hero-actions">
                            <Link className="button button-primary button-large" to="/login">
                                Sign in to RollNexa <ArrowRight size={17} />
                            </Link>
                            <Link className="button button-outline button-large" to="/features">Explore the platform</Link>
                        </div>
                        <div className="hero-assurance">
                            <ShieldCheck size={17} />
                            <span>Role-based access. Structured records. A verification-first attendance model.</span>
                        </div>
                    </div>
                    <div className="hero-visual" aria-label="Illustration of the RollNexa attendance workflow">
                        <div className="hero-visual-orbit orbit-one" />
                        <div className="hero-visual-orbit orbit-two" />
                        <div className="product-preview-card">
                            <div className="preview-card-top">
                                <div className="preview-brand">
                                    <img src="/static/images/rollnexa-mark.svg" alt="" />
                                    <span>RollNexa</span>
                                </div>
                                <span className="preview-status"><i /> WORKFLOW PREVIEW</span>
                            </div>
                            <div className="preview-heading">
                                <span>ATTENDANCE VERIFICATION</span>
                                <strong>Two checks. One trusted record.</strong>
                            </div>
                            <div className="verification-step">
                                <span className="verification-icon qr-icon"><QrCode size={22} /></span>
                                <span className="verification-copy"><strong>QR session access</strong><small>Confirm the active class session</small></span>
                                <span className="step-state">01</span>
                            </div>
                            <div className="verification-connector"><span /></div>
                            <div className="verification-step">
                                <span className="verification-icon face-icon"><ScanFace size={22} /></span>
                                <span className="verification-copy"><strong>Facial identity check</strong><small>Verify the enrolled student</small></span>
                                <span className="step-state">02</span>
                            </div>
                            <div className="preview-result">
                                <span className="result-icon"><CheckCircle2 size={18} /></span>
                                <span><strong>Attendance record</strong><small>Created only after both checks succeed</small></span>
                            </div>
                            <div className="preview-disclaimer">Verification technologies are introduced in staged releases.</div>
                        </div>
                        <div className="floating-note note-top"><span className="floating-note-icon"><Layers3 size={16} /></span> Academic records</div>
                        <div className="floating-note note-bottom"><span className="floating-note-icon"><ShieldCheck size={16} /></span> Verification-first design</div>
                    </div>
                </div>
            </section>

            <section className="value-strip">
                <div className="container value-strip-inner">
                    <span className="value-strip-label">ONE CONNECTED PLATFORM</span>
                    <div><b>01</b> Academic structure</div>
                    <div><b>02</b> Course coordination</div>
                    <div><b>03</b> Attendance integrity</div>
                </div>
            </section>

            <section className="section section-white">
                <div className="container">
                    <div className="section-heading section-heading-center">
                        <span className="eyebrow">A CLEARER INSTITUTIONAL WORKFLOW</span>
                        <h2>Designed around the work institutions already do.</h2>
                        <p>RollNexa connects the academic records that support teaching with a structured approach to attendance verification.</p>
                    </div>
                    <div className="feature-card-grid">
                        <article className="feature-card">
                            <span className="feature-icon feature-icon-teal"><Building2Icon /></span>
                            <span className="feature-kicker">ACADEMIC FOUNDATION</span>
                            <h3>Organised academic records</h3>
                            <p>Maintain faculties, departments, programmes, academic sessions, courses and course offerings in one connected system.</p>
                            <Link to="/features" className="text-link">Explore academic management <ArrowRight size={15} /></Link>
                        </article>
                        <article className="feature-card">
                            <span className="feature-icon feature-icon-blue"><Users size={22} /></span>
                            <span className="feature-kicker">ROLE-BASED WORKSPACES</span>
                            <h3>Clear responsibilities</h3>
                            <p>Give administrators, lecturers and students access to the records and workflows appropriate to their roles.</p>
                            <Link to="/features" className="text-link">Explore platform features <ArrowRight size={15} /></Link>
                        </article>
                        <article className="feature-card">
                            <span className="feature-icon feature-icon-amber"><Fingerprint size={22} /></span>
                            <span className="feature-kicker">ATTENDANCE INTEGRITY</span>
                            <h3>Verification before recording</h3>
                            <p>The attendance design requires QR session verification followed by facial identity verification before presence is recorded.</p>
                            <Link to="/how-it-works" className="text-link">See the workflow <ArrowRight size={15} /></Link>
                        </article>
                    </div>
                </div>
            </section>

            <section className="section section-mist">
                <div className="container workflow-band">
                    <div className="workflow-copy">
                        <span className="eyebrow">THE ATTENDANCE MODEL</span>
                        <h2>Session access is not the same as identity.</h2>
                        <p>RollNexa separates the question of whether a student is accessing the correct class session from the question of whether the student is who they claim to be.</p>
                        <Link to="/how-it-works" className="button button-dark">Understand the workflow <ArrowRight size={16} /></Link>
                    </div>
                    <div className="workflow-steps">
                        <div className="workflow-step"><span>01</span><QrCode size={21} /><div><strong>QR Code</strong><small>Session access verification</small></div></div>
                        <div className="workflow-step"><span>02</span><ScanFace size={21} /><div><strong>Facial recognition</strong><small>Student identity verification</small></div></div>
                        <div className="workflow-step workflow-step-final"><span>03</span><CheckCircle2 size={21} /><div><strong>Attendance record</strong><small>Recorded only when both checks succeed</small></div></div>
                    </div>
                </div>
            </section>

            <section className="closing-section">
                <div className="container closing-inner">
                    <div>
                        <span className="eyebrow eyebrow-light">ROLLNEXA</span>
                        <h2>Bring your academic workflows together.</h2>
                        <p>Access is managed by authorised institutional administrators. Sign in with your RollNexa account to continue.</p>
                    </div>
                    <Link className="button button-light" to="/login">Sign in to RollNexa <ArrowUpRight size={17} /></Link>
                </div>
            </section>
        </>
    );
}

function Building2Icon() {
    return <Building2 size={22} />;
}

export function AboutPage() {
    return (
        <>
            <PageIntro
                eyebrow="ABOUT ROLLNEXA"
                title="A connected foundation for academic administration."
                description="RollNexa is being developed to help institutions organise academic information and strengthen the integrity of attendance records through a structured, role-based platform."
            />
            <section className="section section-white">
                <div className="container two-column-section">
                    <div>
                        <span className="eyebrow">THE PURPOSE</span>
                        <h2>Make academic information easier to manage and attendance easier to trust.</h2>
                    </div>
                    <div className="prose-block">
                        <p>Academic administration depends on connected information: who is enrolled, which courses are offered, which lecturers are assigned and when teaching activities take place.</p>
                        <p>RollNexa brings these relationships into a shared system. Its attendance model adds a verification sequence in which a student first accesses an active session using a QR Code and then completes facial identity verification.</p>
                        <p>The platform is being delivered in stages. Existing academic management capabilities are retained as the user-facing experience moves to React.</p>
                    </div>
                </div>
            </section>
            <section className="section section-mist">
                <div className="container value-grid">
                    <article><span className="value-icon"><BookOpen size={21} /></span><h3>Structured information</h3><p>Keep academic entities and their relationships organised and consistent.</p></article>
                    <article><span className="value-icon"><ShieldCheck size={21} /></span><h3>Accountable access</h3><p>Use role-based access and server-side permission checks for institutional workflows.</p></article>
                    <article><span className="value-icon"><Fingerprint size={21} /></span><h3>Verification-led attendance</h3><p>Require both session access and identity verification before a present record is created.</p></article>
                </div>
            </section>
        </>
    );
}

export function FeaturesPage() {
    const features = [
        { icon: <Building2Icon />, title: "Institutional structure", text: "Manage faculties, departments and programmes while preserving their relationships." },
        { icon: <CalendarDaysIcon />, title: "Academic calendar", text: "Configure academic sessions, semesters and the current academic period." },
        { icon: <BookOpen size={22} />, title: "Course management", text: "Maintain the course catalogue, programme-specific offerings and registration rules." },
        { icon: <Users size={22} />, title: "User and role management", text: "Create and manage administrator, lecturer and student accounts with role-based access." },
        { icon: <QrCode size={22} />, title: "QR session verification", text: "Planned dynamic, session-specific QR codes with server-side validation and expiry." },
        { icon: <ScanFace size={22} />, title: "Facial identity verification", text: "Planned facial enrolment and matching as the second required attendance check." },
        { icon: <FileBarChartIcon />, title: "Attendance reporting", text: "A planned reporting layer for session history, attendance summaries and exports." },
        { icon: <ShieldCheck size={22} />, title: "Access and audit controls", text: "Enforce permissions on the server and retain important academic and attendance history." },
    ];

    return (
        <>
            <PageIntro
                eyebrow="THE ROLLNEXA PLATFORM"
                title="The academic workflow, in one place."
                description="RollNexa connects institutional structure, course administration and a verification-first attendance model. Capabilities are released in stages and are identified below by their current implementation status."
            />
            <section className="section section-white">
                <div className="container">
                    <div className="feature-detail-grid">
                        {features.map((feature, index) => (
                            <article className="feature-detail-card" key={feature.title}>
                                <span className="feature-icon feature-icon-teal">{feature.icon}</span>
                                <div className="feature-detail-title"><h3>{feature.title}</h3><span className={`status-tag ${index < 4 || index === 7 ? "status-available" : "status-planned"}`}>{index < 4 || index === 7 ? "Available foundation" : "Planned"}</span></div>
                                <p>{feature.text}</p>
                            </article>
                        ))}
                    </div>
                </div>
            </section>
            <section className="section section-mist">
                <div className="container feature-note">
                    <span className="feature-note-icon"><Clock3 size={21} /></span>
                    <div><strong>Features are introduced in controlled releases.</strong><p>QR scanning, facial enrolment, facial matching and attendance analytics are not represented as operational until their implementation and testing are complete.</p></div>
                </div>
            </section>
        </>
    );
}

export function HowItWorksPage() {
    const steps = [
        { number: "01", icon: <CalendarDaysIcon />, title: "A lecturer opens a session", text: "An authorised lecturer creates an attendance session for a course offering they are actively assigned to. The session has a defined start and end time." },
        { number: "02", icon: <QrCode size={23} />, title: "The student verifies session access", text: "The student scans the session's time-limited QR Code. The server validates the token, session status, expiry and course registration." },
        { number: "03", icon: <ScanFace size={23} />, title: "The student verifies identity", text: "The system captures a live face sample and compares it with the student's previously enrolled facial reference, subject to liveness and quality checks." },
        { number: "04", icon: <CheckCircle2 size={23} />, title: "Attendance is recorded", text: "Only after both checks succeed, in the required order and within the session window, does the server create a present record." },
    ];

    return (
        <>
            <PageIntro
                eyebrow="HOW IT WORKS"
                title="Two independent checks. One attendance decision."
                description="The agreed RollNexa attendance policy requires successful QR Code verification followed by successful facial identity verification. Neither check is sufficient on its own."
            />
            <section className="section section-white">
                <div className="container">
                    <div className="implementation-note">
                        <Clock3 size={18} />
                        <span>This page describes the agreed target workflow. QR scanning, facial enrolment and facial recognition are planned capabilities and are not yet operational in this release.</span>
                    </div>
                    <div className="process-list">
                        {steps.map((step) => (
                            <article className="process-item" key={step.number}>
                                <span className="process-number">{step.number}</span>
                                <span className="process-icon">{step.icon}</span>
                                <div><h3>{step.title}</h3><p>{step.text}</p></div>
                            </article>
                        ))}
                    </div>
                </div>
            </section>
            <section className="section section-mist">
                <div className="container decision-panel">
                    <div><span className="eyebrow">ATTENDANCE DECISION</span><h2>Both verification outcomes must be successful.</h2></div>
                    <div className="decision-rules">
                        <div><CheckCircle2 size={18} /><span>QR verification succeeds</span></div>
                        <div><CheckCircle2 size={18} /><span>Facial verification succeeds after QR</span></div>
                        <div className="decision-result"><ShieldCheck size={19} /><strong>Present record may be created</strong></div>
                    </div>
                </div>
            </section>
        </>
    );
}

export function ContactPage() {
    return (
        <>
            <PageIntro
                eyebrow="CONTACT"
                title="Need access to RollNexa?"
                description="RollNexa accounts are created and managed by authorised administrators within each institution."
            />
            <section className="section section-white">
                <div className="container contact-grid">
                    <div className="contact-card contact-card-primary">
                        <span className="contact-card-icon"><GraduationCap size={23} /></span>
                        <h2>For students and lecturers</h2>
                        <p>Contact your department, faculty or institution's designated RollNexa administrator if you need an account, have trouble signing in or need your account details updated.</p>
                    </div>
                    <div className="contact-card">
                        <span className="contact-card-icon"><Users size={23} /></span>
                        <h2>For institutional administrators</h2>
                        <p>Use your authorised administrator account to manage institutional structure, user accounts, academic sessions and course information.</p>
                        <Link to="/login" className="text-link">Sign in to the platform <ArrowRight size={15} /></Link>
                    </div>
                </div>
            </section>
        </>
    );
}

export function PrivacyPage() {
    return (
        <>
            <PageIntro eyebrow="PRIVACY INFORMATION" title="Privacy is part of the system design." description="This overview describes the data categories and safeguards relevant to the current RollNexa platform and its planned attendance capabilities." />
            <section className="section section-white">
                <div className="container legal-content">
                    <div className="legal-review-note"><ShieldCheck size={19} /><span>This product overview is not a substitute for an institution-approved privacy notice. Each deploying institution must publish its controller details, lawful basis, retention schedule and contact route before collecting personal or biometric data.</span></div>
                    <h2>Information used by the current platform</h2>
                    <p>The existing platform processes account details, role and institutional profile information, academic structure, course assignments, course registrations and attendance-session administration records.</p>
                    <h2>Planned biometric processing</h2>
                    <p>Facial enrolment and recognition are planned capabilities. The current attendance foundation does not capture facial images or store biometric templates. Biometric processing must not be enabled until the institution has approved its privacy notice, security controls, retention and deletion rules, access restrictions and an appropriate alternative process.</p>
                    <h2>Access and security</h2>
                    <p>Access to platform functions is role-based and enforced by the Django backend. The platform is designed to use authenticated sessions, CSRF protection and restricted access to institutional records.</p>
                    <h2>Institutional responsibility</h2>
                    <p>The institution operating RollNexa is responsible for determining its applicable data-protection obligations, communicating them to users and responding to requests concerning their personal information.</p>
                </div>
            </section>
        </>
    );
}

export function TermsPage() {
    return (
        <>
            <PageIntro eyebrow="TERMS OF USE" title="Using the RollNexa platform." description="These preliminary usage principles describe the intended use of RollNexa. The deploying institution must approve and publish its binding terms before operational use." />
            <section className="section section-white">
                <div className="container legal-content">
                    <div className="legal-review-note"><ShieldCheck size={19} /><span>Institutional review required: these preliminary principles are not a final legal agreement.</span></div>
                    <h2>Authorised access</h2>
                    <p>Users should access RollNexa only through accounts provisioned by an authorised institutional administrator. Users are responsible for protecting their credentials and reporting suspected unauthorised access.</p>
                    <h2>Permitted use</h2>
                    <p>The platform is intended for institutional academic administration and attendance workflows. Users must not attempt to access records outside their authorised role or interfere with the availability, security or integrity of the service.</p>
                    <h2>Academic and attendance records</h2>
                    <p>Users must provide accurate information and use attendance functions only for their intended institutional purpose. Attendance is recorded only after the verification requirements configured by the platform are satisfied.</p>
                    <h2>Availability and staged functionality</h2>
                    <p>RollNexa is released in stages. A feature described on the public website as planned is not necessarily available for operational use. Institutions should rely on the deployed release and its administrator guidance when determining available functionality.</p>
                    <h2>Institutional policies</h2>
                    <p>Use of RollNexa remains subject to the institution's applicable academic, information-security, acceptable-use and data-protection policies.</p>
                </div>
            </section>
        </>
    );
}

function CalendarDaysIcon() {
    return <CalendarDays size={23} />;
}

function FileBarChartIcon() {
    return <FileBarChart size={22} />;
}
