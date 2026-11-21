import { useParams } from "react-router-dom";
import { RolesPage } from "./RolesPage";

export function RolePermissionsPage() {
  const { id } = useParams();
  return <RolesPage initialRoleId={id} />;
}
