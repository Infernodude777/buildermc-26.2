package net.infernodude777.buildermc.block;

import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.entity.player.PlayerInventory;
import net.minecraft.screen.CraftingScreenHandler;
import net.minecraft.screen.ScreenHandlerContext;
import net.minecraft.screen.ScreenHandlerType;

/**
 * Screen handler for the Builder's Workbench.
 * Currently extends the crafting table behavior as a base.
 * Future: add blueprint slots and specialized builder recipes.
 */
public class BuildersWorkbenchScreenHandler extends CraftingScreenHandler {

    private final ScreenHandlerContext context;

    public BuildersWorkbenchScreenHandler(int syncId, PlayerInventory playerInventory, ScreenHandlerContext context) {
        super(ScreenHandlerType.CRAFTING, syncId, playerInventory, context);
        this.context = context;
    }

    @Override
    public boolean canUse(PlayerEntity player) {
        return context.get((world, pos) ->
            world.getBlockState(pos).getBlock() instanceof BuildersWorkbenchBlock, true
        );
    }
}
