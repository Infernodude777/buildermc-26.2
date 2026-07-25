package net.infernodude777.buildermc.block;

import net.minecraft.block.Block;
import net.minecraft.block.BlockState;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.screen.NamedScreenHandlerFactory;
import net.minecraft.screen.ScreenHandlerContext;
import net.minecraft.screen.SimpleNamedScreenHandlerFactory;
import net.minecraft.text.Text;
import net.minecraft.util.ActionResult;
import net.minecraft.util.hit.BlockHitResult;
import net.minecraft.util.math.BlockPos;
import net.minecraft.world.World;

/**
 * Builder's Workbench — a specialized crafting station for builder items.
 *
 * Opens a custom crafting interface when right-clicked.
 * Future: expand with blueprint storage and recipe unlocks.
 */
public class BuildersWorkbenchBlock extends Block {

    private static final Text TITLE = Text.translatable("container.buildermc.builders_workbench");

    public BuildersWorkbenchBlock(Settings settings) {
        super(settings);
    }

    @Override
    public ActionResult onUse(BlockState state, World world, BlockPos pos, PlayerEntity player, BlockHitResult hit) {
        if (world.isClient) {
            return ActionResult.SUCCESS;
        }

        player.openHandledScreen(createScreenHandlerFactory(state, world, pos));
        return ActionResult.SUCCESS;
    }

    @Override
    public NamedScreenHandlerFactory createScreenHandlerFactory(BlockState state, World world, BlockPos pos) {
        return new SimpleNamedScreenHandlerFactory(
            (syncId, inventory, player) ->
                new BuildersWorkbenchScreenHandler(syncId, inventory, ScreenHandlerContext.create(world, pos)),
            TITLE
        );
    }
}
