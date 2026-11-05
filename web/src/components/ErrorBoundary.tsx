import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Unhandled YatraSathi client error caught by ErrorBoundary:', error, errorInfo);
    this.setState({ error, errorInfo });
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#FFF8F6] text-[#201A18] flex items-center justify-center p-6">
          <div className="max-w-xl w-full bg-white/90 backdrop-blur-xl border border-[#E8DDD3] rounded-3xl p-8 sm:p-10 shadow-[0_16px_50px_rgba(42,36,33,0.08)] text-center space-y-6">
            {/* Status Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-amber-50 border border-amber-200 text-[#9D3E19] text-xs font-bold uppercase tracking-wider">
              <AlertTriangle className="w-4 h-4 text-[#9D3E19]" />
              <span>Telemetry Alert • High-Altitude Disruption</span>
            </div>

            {/* Error Message */}
            <div className="space-y-2">
              <h1 className="text-2xl sm:text-3xl font-serif-yatra font-bold text-[#201A18]">
                Something Unexpected Occurred on the Trail
              </h1>
              <p className="text-xs sm:text-sm text-[#56423B] leading-relaxed">
                The application encountered a client-side execution interruption. 
                Your saved journeys and profile ledgers remain safely intact.
              </p>
            </div>

            {/* Collapsible Error Details for Developers */}
            {this.state.error && (
              <details className="text-left bg-[#FDF1EC] border border-[#E8DDD3] rounded-xl p-3 text-xs font-mono text-[#8A726A] cursor-pointer">
                <summary className="font-bold text-[#201A18] hover:text-[#9D3E19]">
                  Inspect Diagnostic Log
                </summary>
                <div className="mt-2 text-[11px] overflow-x-auto text-[#9D3E19] break-words whitespace-pre-wrap">
                  {this.state.error.toString()}
                </div>
              </details>
            )}

            {/* Recovery Action Buttons */}
            <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
              <button
                onClick={this.handleReset}
                className="px-5 py-2.5 rounded-xl bg-[#9D3E19] text-white font-bold text-xs shadow-xs hover:bg-[#803012] transition-all flex items-center gap-2 cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Recalibrate &amp; Reload</span>
              </button>
              <a
                href="/"
                className="px-5 py-2.5 rounded-xl bg-[#FDF1EC] text-[#56423B] font-bold text-xs border border-[#E8DDD3] hover:bg-[#F8EBE6] hover:text-[#201A18] transition-all flex items-center gap-2 cursor-pointer"
              >
                <Home className="w-3.5 h-3.5" />
                <span>Return to Home</span>
              </a>
            </div>

            <div className="text-[11px] text-[#8A726A] pt-4 border-t border-[#E8DDD3]">
              If this persistence issue continues, check our{' '}
              <a href="/info" className="text-[#9D3E19] font-bold underline hover:text-[#803012]">
                System Architecture Whitepaper
              </a>{' '}
              or submit a dispatch on{' '}
              <a href="/trail-watch" className="text-[#9D3E19] font-bold underline hover:text-[#803012]">
                Trail Watch
              </a>.
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
