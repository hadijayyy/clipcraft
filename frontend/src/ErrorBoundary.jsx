import { Component } from 'react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null, info: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught:', error, info);
    this.setState({ info });
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen bg-slate-900 text-slate-100 flex items-center justify-center p-6">
          <div className="card max-w-lg w-full text-center">
            <div className="text-5xl mb-4">⚠️</div>
            <h1 className="text-2xl font-bold mb-2">Something went wrong</h1>
            <p className="text-slate-400 mb-4 text-sm">
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <details className="text-left text-xs text-slate-500 mb-6 max-h-40 overflow-y-auto bg-slate-800 rounded-lg p-3">
              <summary className="cursor-pointer text-slate-400 hover:text-slate-300">Stack trace</summary>
              <pre className="mt-2 whitespace-pre-wrap font-mono text-xs">
                {this.state.error?.stack || 'No stack trace available'}
              </pre>
            </details>
            <button
              onClick={() => window.location.reload()}
              className="btn"
              aria-label="Reload page"
            >
              🔄 Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
