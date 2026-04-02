export default function VitalCard({ title, value, unit, icon: Icon, color, status }) {
    const statusColors = {
      Normal: 'bg-green-100 text-green-700',
      Warning: 'bg-yellow-100 text-yellow-700',
      Danger: 'bg-red-100 text-red-700',
      '--': 'bg-slate-100 text-slate-500',
    };
  
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-5">
        <div className="flex items-start justify-between mb-3">
          <div className="p-2.5 rounded-lg" style={{ backgroundColor: `${color}15` }}>
            <Icon size={22} style={{ color }} />
          </div>
          <span className={`text-xs font-medium px-2 py-1 rounded-full ${statusColors[status] || statusColors['--']}`}>
            {status || '--'}
          </span>
        </div>
        <div className="mt-2">
          <p className="text-slate-500 text-sm">{title}</p>
          <div className="flex items-end gap-1 mt-1">
            <span className="text-4xl font-bold text-slate-800" style={{ lineHeight: 1.1 }}>
              {value !== null && value !== undefined ? value : '--'}
            </span>
            <span className="text-slate-400 text-sm mb-1">{unit}</span>
          </div>
        </div>
      </div>
    );
  }