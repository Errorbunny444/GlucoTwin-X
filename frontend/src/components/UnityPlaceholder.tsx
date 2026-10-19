

export function UnityPlaceholder() {
  return (
    <div className="p-4 bg-gray-800 rounded shadow h-full min-h-[300px] flex flex-col">
      <h3 className="text-sm font-medium text-gray-400 uppercase mb-4">3D Metabolic Twin</h3>
      <div className="flex-1 border-2 border-dashed border-gray-700 rounded-lg flex items-center justify-center bg-gray-800/50">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-3 text-gray-600">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5" />
            </svg>
          </div>
          <p className="text-gray-400 font-medium">Unity Digital Twin will appear here.</p>
          <p className="text-gray-600 text-sm mt-2">Reserved for Phase 7 implementation.</p>
        </div>
      </div>
    </div>
  );
}
