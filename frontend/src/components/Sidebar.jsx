import api from "../api/axios";

function sourceIcon(contentType) {
  if (!contentType) return "📄";
  if (contentType === "application/pdf") return "📄";
  if (contentType === "text/html") return "🌐";
  if (contentType === "text/plain") return "🐙"; // GitHub file imports
  if (contentType.startsWith("image/")) return "🖼️";
  return "📄";
}

export default function Sidebar({
  documents,
  selectedDocument,
  setSelectedDocument,
  fetchDocuments,
  isOpen,
  onClose,
}) {

  const handleDelete = async (id) => {

    const confirmDelete = window.confirm(
      "Delete this document?"
    );

    if (!confirmDelete) return;

    try {

      await api.delete(`/documents/${id}`);

      if (
        selectedDocument &&
        selectedDocument.id === id
      ) {
        setSelectedDocument(null);
      }

      fetchDocuments();

    } catch (err) {

      console.error(err);

      alert(
        err.response?.data?.detail ||
        "Delete failed."
      );

    }

  };

  return (
    <>
      {/* Mobile-only backdrop, closes the drawer on tap outside it */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={onClose}
        />
      )}

      <div
        className={`fixed inset-y-0 left-0 z-40 w-64 bg-gray-50 p-4 border-r border-gray-200
          transform transition-transform duration-200 ease-in-out
          lg:static lg:z-auto lg:w-64 lg:translate-x-0
          ${isOpen ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-800">
            Documents
          </h2>
          <button
            onClick={onClose}
            className="lg:hidden text-gray-500 hover:text-gray-700 text-xl"
            aria-label="Close menu"
          >
            ✕
          </button>
        </div>

        <div className="space-y-2 overflow-y-auto max-h-[calc(100vh-120px)]">

          {documents.length === 0 ? (

            <p className="text-gray-500 text-sm">
              No documents uploaded.
            </p>

          ) : (

            documents.map((doc) => (

              <div
                key={doc.id}
                className={`rounded-lg p-3 transition-all ${
                  selectedDocument?.id === doc.id
                    ? "bg-blue-100 border border-blue-200"
                    : "bg-white border border-gray-200 hover:bg-gray-100"
                }`}
              >

                <div
                  className="cursor-pointer break-words text-gray-800 text-sm mb-2"
                  onClick={() => {
                    setSelectedDocument(doc);
                    onClose && onClose();
                  }}
                >
                  {sourceIcon(doc.content_type)} {doc.filename}
                </div>

                <button
                  onClick={() => handleDelete(doc.id)}
                  className="text-xs text-red-600 hover:text-red-800 px-2 py-1 rounded-md hover:bg-red-50 transition-colors"
                >
                  Delete
                </button>

              </div>

            ))

          )}

        </div>

      </div>
    </>
  );

}
