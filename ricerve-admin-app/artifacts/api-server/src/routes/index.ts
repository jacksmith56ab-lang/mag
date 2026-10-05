import { Router, type IRouter } from "express";
import healthRouter from "./health";
import ricerveAdminRouter from "./ricerve-admin";

const router: IRouter = Router();

router.use(healthRouter);
router.use(ricerveAdminRouter);

export default router;
