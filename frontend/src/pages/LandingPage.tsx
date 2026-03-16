import GitHubInput from "../components/landing/GitHubInput";
import ZipUpload from "../components/landing/ZipUpload";
import ProjectList from "../components/landing/ProjectList";

export default function LandingPage() {
  return (
    <div className="min-h-full flex flex-col items-center justify-start py-16 px-4">
      <div className="mb-12 text-center">
        <h1 className="text-3xl font-semibold text-gray-100 tracking-tight mb-2">
          Code Graph
        </h1>
        <p className="text-gray-500 text-sm max-w-md">
          Semantic code intelligence — explore structure, dependencies, and call
          flows across any codebase.
        </p>
      </div>

      <div className="card w-full max-w-xl p-6 flex flex-col gap-6 mb-8">
        <GitHubInput />
        <div className="flex items-center gap-3">
          <hr className="flex-1 border-surface-border" />
          <span className="text-xs text-gray-600">or</span>
          <hr className="flex-1 border-surface-border" />
        </div>
        <ZipUpload />
      </div>

      <div className="w-full max-w-xl">
        <h2 className="text-xs text-gray-500 uppercase tracking-widest mb-3">
          Recent Projects
        </h2>
        <ProjectList />
      </div>
    </div>
  );
}
