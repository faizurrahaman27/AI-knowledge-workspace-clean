export default function ChatInput() {
  return (
    <div className="border-t border-slate-700 p-5 flex gap-4">

      <input
        type="text"
        placeholder="Ask anything..."
        className="flex-1 p-3 rounded-lg bg-slate-700 text-white outline-none"
      />

      <button className="bg-blue-600 hover:bg-blue-700 px-6 rounded-lg text-white">
        Send
      </button>

    </div>
  );
}