interface StatCardProps {
  title: string;
  value: string | number;
  icon?: React.ReactNode;
  color?: "blue" | "green" | "red" | "yellow";
  trend?: {
    value: number;
    direction: "up" | "down";
  };
}

const colorClasses = {
  blue: "bg-blue-50 text-blue-600 border-blue-200",
  green: "bg-green-50 text-green-600 border-green-200",
  red: "bg-red-50 text-red-600 border-red-200",
  yellow: "bg-yellow-50 text-yellow-600 border-yellow-200",
};

export default function StatCard({
  title,
  value,
  icon,
  color = "blue",
  trend,
}: StatCardProps) {
  return (
    <div className={`${colorClasses[color]} p-6 rounded-lg border`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium opacity-75">{title}</p>
          <p className="text-3xl font-bold mt-2">{value}</p>
          {trend && (
            <p
              className={`text-sm mt-2 ${trend.direction === "up" ? "text-green-600" : "text-red-600"}`}
            >
              {trend.direction === "up" ? "↑" : "↓"} {trend.value}%
            </p>
          )}
        </div>
        {icon && <div className="text-4xl opacity-50">{icon}</div>}
      </div>
    </div>
  );
}
