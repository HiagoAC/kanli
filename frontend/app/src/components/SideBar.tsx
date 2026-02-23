import { Box, Divider, Link, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import logo from "../assets/kanli_logo.png";
import { SideBarBoardList } from "../features/board/components/SideBarBoardList";
import { SideBarButtonList } from "./SideBarButtonList";

export function SideBar() {
	return (
		<Box
			sx={{
				height: "100vh",
				display: "flex",
				flexDirection: "column",
				borderRight: "1px solid",
				borderColor: "divider",
			}}
		>
			<Link component={RouterLink} to="/" underline="none" color="inherit">
				<Box
					sx={{
						display: "flex",
						alignItems: "center",
						gap: 1,
						m: 2,
					}}
				>
					<Box
						component="img"
						src={logo}
						alt="Kanli Logo"
						sx={{ width: "40px", height: "40px" }}
					/>
					<Typography variant="h4" fontWeight="bold">
						Kanli
					</Typography>
				</Box>
			</Link>
			<SideBarButtonList />
			<Divider />
			<Box sx={{ flexGrow: 1, overflowY: "auto" }}>
				<SideBarBoardList />
			</Box>
		</Box>
	);
}
