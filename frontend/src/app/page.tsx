import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Activity, BarChart3, Bell, Globe, Shield, Zap } from 'lucide-react';

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      {/* Header */}
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">API Monitor</span>
          </div>
          <nav className="flex items-center gap-4">
            <Link href="/login">
              <Button variant="ghost">Sign in</Button>
            </Link>
            <Link href="/register">
              <Button>Get Started</Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container flex flex-col items-center justify-center gap-8 py-24 text-center md:py-32">
        <div className="space-y-4">
          <h1 className="text-4xl font-bold tracking-tighter sm:text-5xl md:text-6xl lg:text-7xl">
            Monitor Your APIs
            <br />
            <span className="gradient-text">With Confidence</span>
          </h1>
          <p className="mx-auto max-w-[700px] text-lg text-muted-foreground md:text-xl">
            Production-ready API monitoring with real-time alerts, beautiful 3D visualizations,
            and comprehensive incident management.
          </p>
        </div>
        <div className="flex flex-col gap-4 sm:flex-row">
          <Link href="/register">
            <Button size="lg" className="gap-2">
              <Zap className="h-4 w-4" />
              Start Monitoring Free
            </Button>
          </Link>
          <Link href="/login">
            <Button size="lg" variant="outline">
              View Demo
            </Button>
          </Link>
        </div>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <Shield className="h-4 w-4" />
            <span>No credit card required</span>
          </div>
          <div className="flex items-center gap-1">
            <Globe className="h-4 w-4" />
            <span>Global monitoring</span>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="border-t bg-muted/50 py-24">
        <div className="container">
          <div className="mb-12 text-center">
            <h2 className="mb-4 text-3xl font-bold tracking-tight sm:text-4xl">
              Everything you need to monitor APIs
            </h2>
            <p className="mx-auto max-w-[700px] text-muted-foreground">
              Comprehensive monitoring features designed for modern development teams
            </p>
          </div>
          <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
            <FeatureCard
              icon={<Activity className="h-8 w-8" />}
              title="Multi-Protocol Monitoring"
              description="Monitor HTTP, HTTPS, TCP, DNS, WebSocket, and gRPC endpoints from multiple regions"
            />
            <FeatureCard
              icon={<Bell className="h-8 w-8" />}
              title="Smart Alerts"
              description="Get notified via Email, Slack, SMS, PagerDuty, or custom webhooks when issues arise"
            />
            <FeatureCard
              icon={<BarChart3 className="h-8 w-8" />}
              title="Detailed Analytics"
              description="Track response times, uptime percentages, and performance trends over time"
            />
            <FeatureCard
              icon={<Globe className="h-8 w-8" />}
              title="3D Visualizations"
              description="Beautiful 3D globe showing your monitors and their status in real-time"
            />
            <FeatureCard
              icon={<Shield className="h-8 w-8" />}
              title="Incident Management"
              description="Automatic incident detection, escalation, and resolution tracking"
            />
            <FeatureCard
              icon={<Zap className="h-8 w-8" />}
              title="Real-time Updates"
              description="Live monitoring with WebSocket updates and instant notifications"
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="border-t py-24">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="mb-4 text-3xl font-bold tracking-tight sm:text-4xl">
              Start monitoring in seconds
            </h2>
            <p className="mb-8 text-lg text-muted-foreground">
              Join teams monitoring millions of API requests every day
            </p>
            <Link href="/register">
              <Button size="lg">Create Free Account</Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t bg-muted/50 py-12">
        <div className="container">
          <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              <span className="font-semibold">API Monitor Platform</span>
            </div>
            <p className="text-sm text-muted-foreground">
              © 2025 API Monitor. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="group relative rounded-lg border bg-card p-6 shadow-sm transition-all hover:shadow-md">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary transition-all group-hover:bg-primary group-hover:text-primary-foreground">
        {icon}
      </div>
      <h3 className="mb-2 font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
