import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("CreditIQ UI error", error, info);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <main className="center-state" role="alert">
          <h1>CreditIQ hit an interface error.</h1>
          <button className="btn primary" onClick={() => window.location.reload()}>
            Reload
          </button>
        </main>
      );
    }
    return this.props.children;
  }
}
