export default function ChatWindow() {
  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-5">

      <div className="bg-blue-600 text-white p-4 rounded-xl ml-auto max-w-xl">
        What are my projects?
      </div>

      <div className="bg-slate-700 text-white p-4 rounded-xl max-w-xl">
        Your uploaded resume mentions two major projects:
        <br /><br />
        • Autonomous Drone Tracking
        <br />
        • AI Question Answering System
      </div>

    </div>
  );
}