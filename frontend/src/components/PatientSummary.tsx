import type { StaticTwinState } from '../types';
import { User } from 'lucide-react';

export function PatientSummary({ staticState }: { staticState: StaticTwinState | null }) {
  if (!staticState) {
    return <div className="p-4 bg-gray-800 rounded shadow animate-pulse h-24"></div>;
  }

  return (
    <div className="p-4 bg-gray-800 rounded shadow flex items-center gap-4">
      <div className="w-12 h-12 rounded-full bg-blue-600 flex items-center justify-center">
        <User size={24} className="text-white" />
      </div>
      <div>
        <h2 className="text-lg font-semibold text-white">{staticState.twin_id}</h2>
        <div className="text-sm text-gray-400">
          {staticState.age} years &bull; {staticState.gender}
        </div>
        <div className="text-sm text-gray-400 mt-1">
          BMI {staticState.bmi.toFixed(1)} &bull; HbA1c {staticState.hba1c.toFixed(1)}%
        </div>
        <div className="text-xs text-gray-500 mt-1">
          Medication Context: {staticState.ehr_has_diabetes_medication ? 'Active' : 'None'}
        </div>
      </div>
    </div>
  );
}
