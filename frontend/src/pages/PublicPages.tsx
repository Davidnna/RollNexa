import {
    ArrowRight,
    ArrowUpRight,
    BookOpen,
    Building2,
    CalendarDays,
    CheckCircle2,
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
                            Manage academic records, coordinate courses and record attendance in one place.
                        </p>
                        <div className="hero-actions">
                            <Link className="button button-primary button-large" to="/login">
                                Sign in to RollNexa <ArrowRight size={17} />
                            </Link>
                            <Link className="button button-outline button-large" to="/features">Explore the platform</Link>
                        </div>
                        <div className="hero-assurance">
                            <ShieldCheck size={17} />
                            <span>One platform for administrators, lecturers and students.</span>
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
                                <span className="verification-copy"><strong>Class code</strong><small>Confirm the class</small></span>
                                <span className="step-state">01</span>
                            </div>
                            <div className="verification-connector"><span /></div>
                            <div className="verification-step">
                                <span className="verification-icon face-icon"><ScanFace size={22} /></span>
                                <span className="verification-copy"><strong>Face check</strong><small>Confirm your identity</small></span>
                                <span className="step-state">02</span>
                            </div>
                            <div className="preview-result">
                                <span className="result-icon"><CheckCircle2 size={18} /></span>
                                <span><strong>Attendance record</strong><small>Created only after both checks succeed</small></span>
                            </div>

                        </div>
                        <div className="floating-note note-top"><span className="floating-note-icon"><Layers3 size={16} /></span> Academic records</div>
                        <div className="floating-note note-bottom"><span className="floating-note-icon"><ShieldCheck size={16} /></span> Reliable attendance</div>
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
                        <h2>The essentials of academic administration, connected.</h2>
                        <p>Keep people, courses and attendance information organised in one place.</p>
                    </div>
                    <div className="feature-card-grid">
                        <article className="feature-card">
                            <span className="feature-icon feature-icon-teal"><Building2Icon /></span>
                            <span className="feature-kicker">ACADEMIC FOUNDATION</span>
                            <h3>Organised academic records</h3>
                            <p>Keep institutional structure, academic sessions and course information organised.</p>
                            <Link to="/features" className="text-link">Explore academic management <ArrowRight size={15} /></Link>
                        </article>
                        <article className="feature-card">
                            <span className="feature-icon feature-icon-blue"><Users size={22} /></span>
                            <span className="feature-kicker">WORKSPACES FOR EVERY ROLE</span>
                            <h3>Clear responsibilities</h3>
                            <p>Give administrators, lecturers and students the tools they need.</p>
                            <Link to="/features" className="text-link">Explore platform features <ArrowRight size={15} /></Link>
                        </article>
                        <article className="feature-card">
                            <span className="feature-icon feature-icon-amber"><Fingerprint size={22} /></span>
                            <span className="feature-kicker">ATTENDANCE INTEGRITY</span>
                            <h3>Verification before recording</h3>
                            <p>Students check in with a class QR Code and a face check.</p>
                            <Link to="/how-it-works" className="text-link">See the workflow <ArrowRight size={15} /></Link>
                        </article>
                    </div>
                </div>
            </section>

            <section className="section section-mist">
                <div className="container workflow-band">
                    <div className="workflow-copy">
                        <span className="eyebrow">THE ATTENDANCE MODEL</span>
                        <h2>A simple, two-step check-in.</h2>
                        <p>Students scan the class code, then confirm their identity. Attendance is recorded after both steps succeed.</p>
                        <Link to="/how-it-works" className="button button-dark">See how it works <ArrowRight size={16} /></Link>
                    </div>
                    <div className="workflow-steps">
                        <div className="workflow-step"><span>01</span><QrCode size={21} /><div><strong>QR Code</strong><small>Confirm the class</small></div></div>
                        <div className="workflow-step"><span>02</span><ScanFace size={21} /><div><strong>Face verification</strong><small>Confirm student identity</small></div></div>
                        <div className="workflow-step workflow-step-final"><span>03</span><CheckCircle2 size={21} /><div><strong>Attendance record</strong><small>Recorded only when both checks succeed</small></div></div>
                    </div>
                </div>
            </section>

            <section className="closing-section">
                <div className="container closing-inner">
                    <div>
                        <span className="eyebrow eyebrow-light">ROLLNEXA</span>
                        <h2>Keep your institution organised.</h2>
                        <p>Sign in with the account provided by your institution.</p>
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
                title="Academic administration, made clearer."
                description="RollNexa helps institutions manage academic information, coordinate teaching and keep reliable attendance records."
            />
            <section className="section section-white">
                <div className="container two-column-section">
                    <div>
                        <span className="eyebrow">THE PURPOSE</span>
                        <h2>Bring everyday academic work into one place.</h2>
                    </div>
                    <div className="prose-block">
                        <p>Institutions work with connected information: students, courses, lecturers, programmes and academic schedules.</p>
                        <p>RollNexa brings these records together. Students check in by scanning the class QR Code and completing a face check.</p>
                        <p>Each person sees the information and tools relevant to their role.</p>
                    </div>
                </div>
            </section>
            <section className="section section-mist">
                <div className="container value-grid">
                    <article><span className="value-icon"><BookOpen size={21} /></span><h3>Structured information</h3><p>Keep departments, programmes and courses organised.</p></article>
                    <article><span className="value-icon"><ShieldCheck size={21} /></span><h3>Accountable access</h3><p>Give each user access to the tasks and information they need.</p></article>
                    <article><span className="value-icon"><Fingerprint size={21} /></span><h3>Reliable attendance</h3><p>Record attendance only after both check-in steps succeed.</p></article>
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
        { icon: <Users size={22} />, title: "User and role management", text: "Manage administrator, lecturer and student accounts." },
        { icon: <QrCode size={22} />, title: "QR Code check-in", text: "Use a time-limited class code to check in to an active session." },
        { icon: <ScanFace size={22} />, title: "Face verification", text: "Confirm your identity with a quick camera check." },
        { icon: <FileBarChartIcon />, title: "Attendance reports", text: "Review class attendance, session history and approved alternatives." },
        { icon: <ShieldCheck size={22} />, title: "Flexible attendance", text: "Students can manage face verification or request an approved alternative when needed." },
    ];

    return (
        <>
            <PageIntro
                eyebrow="THE ROLLNEXA PLATFORM"
                title="Academic work, in one place."
                description="Everything institutions need to organise academic activity and manage attendance."
            />
            <section className="section section-white">
                <div className="container">
                    <div className="feature-detail-grid">
                        {features.map((feature) => (
                            <article className="feature-detail-card" key={feature.title}>
                                <span className="feature-icon feature-icon-teal">{feature.icon}</span>
                                <div className="feature-detail-title"><h3>{feature.title}</h3></div>
                                <p>{feature.text}</p>
                            </article>
                        ))}
                    </div>
                </div>
            </section>
            <section className="section section-mist">
                <div className="container feature-note">
                    <span className="feature-note-icon"><ShieldCheck size={21} /></span>
                    <div><strong>Attendance with an alternative.</strong><p>Automated check-in requires both the class QR Code and face verification. Students who cannot use face verification can ask their lecturer for an approved alternative.</p></div>
                </div>
            </section>
        </>
    );
}

export function HowItWorksPage() {
    const steps = [
        { number: "01", icon: <CalendarDaysIcon />, title: "Your lecturer opens the class", text: "Your lecturer starts an attendance session for the course." },
        { number: "02", icon: <QrCode size={23} />, title: "Scan the class code", text: "Scan the QR Code displayed by your lecturer." },
        { number: "03", icon: <ScanFace size={23} />, title: "Confirm your identity", text: "Look at the camera and follow the short on-screen prompt. RollNexa completes the check automatically." },
        { number: "04", icon: <CheckCircle2 size={23} />, title: "You're checked in", text: "Your attendance is recorded when both checks succeed. An approved alternative is available if you cannot use face verification." },
    ];

    return (
        <>
            <PageIntro
                eyebrow="HOW IT WORKS"
                title="Check in with two simple steps."
                description="Scan the class QR Code, then confirm your identity. Your attendance is recorded after both steps succeed."
            />
            <section className="section section-white">
                <div className="container">

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
                    <div><span className="eyebrow">ATTENDANCE DECISION</span><h2>Both steps must be complete.</h2></div>
                    <div className="decision-rules">
                        <div><CheckCircle2 size={18} /><span>Scan the class code</span></div>
                        <div><CheckCircle2 size={18} /><span>Confirm your identity</span></div>
                        <div className="decision-result"><ShieldCheck size={19} /><strong>Attendance recorded</strong></div>
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
                title="Need help with access?"
                description="Your institution manages RollNexa accounts."
            />
            <section className="section section-white">
                <div className="container contact-grid">
                    <div className="contact-card contact-card-primary">
                        <span className="contact-card-icon"><GraduationCap size={23} /></span>
                        <h2>For students and lecturers</h2>
                        <p>Contact your institution if you need an account or help signing in.</p>
                    </div>
                    <div className="contact-card">
                        <span className="contact-card-icon"><Users size={23} /></span>
                        <h2>For institutional administrators</h2>
                        <p>Sign in to manage users, academic information and attendance.</p>
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
            <PageIntro eyebrow="PRIVACY INFORMATION" title="How RollNexa uses your information." description="This notice explains what information RollNexa uses and how it is handled." />
            <section className="section section-white">
                <div className="container legal-content">
                    <div className="legal-review-note"><ShieldCheck size={19} /><span>Your institution is responsible for its privacy notice, lawful basis, retention periods and privacy contact details. Confirm these with your institution before using face verification.</span></div>
                    <h2>Information we use</h2>
                    <p>RollNexa uses your account details, institutional profile, course registrations and attendance records to provide the service.</p>
                    <h2>Face verification</h2>
                    <p>Your camera reads the class QR Code and captures your face during enrolment and check-in. Camera images are sent securely for verification and processed temporarily; RollNexa does not save them as photographs. RollNexa stores an encrypted face record and limited attendance-verification information.</p>
                    <h2>Consent and alternative attendance</h2>
                    <p>Face verification is optional and requires your consent. You can withdraw consent at any time; your stored face record will be deleted. If you do not consent or cannot complete the check, ask your lecturer about the approved attendance alternative.</p>
                    <h2>Access and security</h2>
                    <p>Access to information is limited according to each user's role. Face records are encrypted and access to institutional information is restricted.</p>
                    <h2>Institutional responsibility</h2>
                    <p>Your institution is responsible for explaining its privacy practices and responding to requests about your information.</p>
                </div>
            </section>
        </>
    );
}

export function TermsPage() {
    return (
        <>
            <PageIntro eyebrow="TERMS OF USE" title="Using RollNexa." description="These terms explain the basic rules for using RollNexa. Your institution may also have additional policies." />
            <section className="section section-white">
                <div className="container legal-content">
                    <div className="legal-review-note"><ShieldCheck size={19} /><span>Follow your institution's academic and information-use policies when using RollNexa.</span></div>
                    <h2>Authorised access</h2>
                    <p>Users should access RollNexa only through accounts provisioned by an authorised institutional administrator. Users are responsible for protecting their credentials and reporting suspected unauthorised access.</p>
                    <h2>Permitted use</h2>
                    <p>The platform is intended for institutional academic administration and attendance workflows. Users must not attempt to access records outside their authorised role or interfere with the availability, security or integrity of the service.</p>
                    <h2>Academic and attendance records</h2>
                    <p>Users must provide accurate information and use attendance functions only for their intended institutional purpose. Attendance is recorded after the class QR Code and face checks succeed. An approved alternative may be recorded separately when face verification cannot be used.</p>
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
